"""
WebuntisAPI is a webuntis timetable API based on "python-webuntis" made for getting every timetable of students, classes, rooms and teachers.

Functions
---------
class WebuntisAPI():
    def get_timetable(s: Session, identifier: TeacherObject | KlassenObject | RoomObject | StudentObject, time_period: tuple[datetime.date, datetime.date] = get_current_week(),  data: list[webuntis.objects.PeriodList] | None = None) -> webuntis.objects.PeriodList:
        Gets the timetable for a student, class, room or teacher
    def login() -> Session:
        Login with the credentials in "config.txt"
    def get_all_identifier(s: Session, category: str) -> TeacherList | KlassenList | RoomList |StudentsList:
        returns every available object within a category
    def get_identifier_by_id_or_name(s: Session, category: str, id_or_name: str) -> TeacherObject | KlassenObject | RoomObject | StudentObject | None:
        returns matching object of Name or Id


Version
-------
1.0.0
"""


try:
    import webuntis
    from webuntis.session import Session
    import webuntis.objects
    import datetime
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed, Future
except ImportError as e:
    raise ImportError(f'Error occurred while importing: {e}. Note: This API is based on "python-webuntis" <pip install webuntis>')


class WebuntisAPI():
    """WebuntisAPI class for getting every timetable of students, classes, rooms and teachers"""

    def __init__(self, server: str, school: str, username: str, password: str, log: bool = False) -> None:
        self.time_period: tuple[datetime.date, datetime.date] = self._get_current_week()
        self.load_students: bool = False
        self.log: bool = log
        self.max_workers: int = 8

        self.session: Session = self.login(server=server, school=school, username=username, password=password)
        self.cache = None

        
    def login(self, server: str, school: str, username: str, password: str) -> Session:
        """
        Login to Webuntis Session

        Parameters
        ----------
        server: str
            Webuntis server addres like "https://schoolid.webuntis.com"
        school: str
            school id
        username: str
            username of user
        password: str
            passord for user
        """
        try:
            s = Session(
                server=server,
                username=username,
                password=password,
                school=school,
                useragent='WebUntisAPI'
            )
            s.login()
        except Exception as e:
            raise RuntimeError(f"Login failed: {e}")
        return s


    def logout(self):
        """Webuntis Session logout"""
        self.session.logout()


    # utils
    def _get_current_week(self) -> tuple[datetime.date, datetime.date]:
        """
        Time period for timetables.

        Get the start and end date of the current week (excluding Weekends).

        Returns
        -------
        monday: datetime.date
            Monday of the week. Except it is weekend, then: Monday of the next week.
        friday: datetiem.date
            Friday of the week. Except it is weekend, then: Friday of the next week.
        """

        ref_date = datetime.date.today()
        if ref_date.weekday() == 5:
            ref_date = ref_date + datetime.timedelta(days=2)
        
        monday = ref_date - datetime.timedelta(days=ref_date.weekday())
        friday = monday + datetime.timedelta(days=4)
        return monday, friday


    def _try_getattr(self, obj: object, attr: str):
        """Try to get attribute of object (Needed because of "bugs" in python-webuntis...)"""
        try:
            return getattr(obj, attr, None)
        except Exception:
            return None



    # caching
    def _load_every_lesson_klassen(self) -> dict[webuntis.objects.StudentObject | webuntis.objects.KlassenObject, webuntis.objects.PeriodList]:
        """
        Load timetables from every class.
        
        Returns
        -------
        timetables: dict[webuntis.objects.KlassenObject, webuntis.objects.PeriodList]
            Dictionary with the owner of the timetables
        """

        start, end = self.time_period
        unloaded_klassen: list[webuntis.objects.KlassenObject] = []
        for klasse in self.session.klassen():
            unloaded_klassen.append(klasse)
        length = len(unloaded_klassen)
        timetables: dict[webuntis.objects.StudentObject | webuntis.objects.KlassenObject, webuntis.objects.PeriodList] = {}
        i = 0

        def klassen_laden(unloaded_klassen: list[webuntis.objects.KlassenObject], timetables: dict[webuntis.objects.StudentObject | webuntis.objects.KlassenObject, webuntis.objects.PeriodList]) -> dict[webuntis.objects.StudentObject | webuntis.objects.KlassenObject, webuntis.objects.PeriodList]:
            with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                tasks: dict[Future[webuntis.objects.PeriodList], webuntis.objects.KlassenObject] = {}
                for klasse in unloaded_klassen:
                    task = pool.submit(self.session.timetable_extended,klasse=klasse,start=start,end=end) # type: ignore
                    tasks[task] = klasse

                for _, task in enumerate(as_completed(tasks), 1):
                    klasse: webuntis.objects.KlassenObject = tasks[task]
                    

                    try:
                        timetables[klasse] = task.result()
                        unloaded_klassen.remove(klasse)
                        if self.log: 
                            progress = round((length - len(unloaded_klassen)) / length * 100)
                            bar_length = 40
                            filled = int(bar_length * progress / 100)
                            bar = '█' * filled + '░' * (bar_length - filled)

                            print("\033[1A\033[2K", end="")
                            print(f"{klasse.name:<15} loaded")
                            print(f"[{bar}] {progress}%", flush=True)


                    except Exception as e:
                        raise RuntimeError(f"Error for {klasse.name}: {e}")
            return timetables

        print("Loading data (parallel)...") if self.log else None
        loading_time_start = time.time()

        while unloaded_klassen and i <= 3 :
            i += 1
            timetables = klassen_laden(unloaded_klassen, timetables)
        
        loading_time_end = time.time()
        if self.log:
            loading_duration = loading_time_end - loading_time_start
            print(f"Loading data completed in {loading_duration:.2f} s.")

        return timetables

        
    def _load_every_lesson_students(self) -> dict[webuntis.objects.StudentObject | webuntis.objects.KlassenObject, webuntis.objects.PeriodList]:
        """
        Load timetables from every student.
        
        Returns
        -------
        timetables: dict[webuntis.objects.StudentObject, webuntis.objects.PeriodList]
            Dictionary with the owner of the timetables
        """
        start, end = self.time_period
        unloaded_students: list[webuntis.objects.StudentObject] = []
        for student in self.session.students():
            unloaded_students.append(student)
        length = len(unloaded_students)
        timetables: dict[webuntis.objects.StudentObject | webuntis.objects.KlassenObject, webuntis.objects.PeriodList] = {}
        i = 0

        def student_laden(unloaded_students: list[webuntis.objects.StudentObject], timetables: dict[webuntis.objects.StudentObject | webuntis.objects.KlassenObject, webuntis.objects.PeriodList]) -> dict[webuntis.objects.StudentObject | webuntis.objects.KlassenObject, webuntis.objects.PeriodList]:
            with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                tasks: dict[Future[webuntis.objects.PeriodList], webuntis.objects.StudentObject] = {}
                for student in unloaded_students:
                    task = pool.submit(self.session.timetable_extended,student=student,start=start,end=end) # type: ignore
                    tasks[task] = student

                for _, task in enumerate(as_completed(tasks), 1):
                    student: webuntis.objects.StudentObject = tasks[task]
                    

                    try:
                        timetables[student] = task.result()
                        unloaded_students.remove(student)
                        if self.log: 
                            progress = round((length - len(unloaded_students)) / length * 100)
                            bar_length = 40
                            filled = int(bar_length * progress / 100)
                            bar = '█' * filled + '░' * (bar_length - filled)

                            print("\033[1A\033[2K", end="")
                            print(f"{student.name:<35} loaded")
                            print(f"[{bar}] {progress}%", flush=True)


                    except Exception as e:
                        raise RuntimeError(f"Error for {student.name}: {e}")
            return timetables

        print("Loading data (parallel)...") if self.log else None
        loading_time_start = time.time()

        while unloaded_students and i <= 3 :
            i += 1
            timetables = student_laden(unloaded_students, timetables)
        
        loading_time_end = time.time()
        if self.log:    
            loading_duration = loading_time_end - loading_time_start
            print(f"Loading data completed in {loading_duration:.2f} s.")

        return timetables


    def _filter_lessons(self, timetables: dict[webuntis.objects.StudentObject | webuntis.objects.KlassenObject, webuntis.objects.PeriodList]) -> webuntis.objects.PeriodList:
        """
        Filters duplications and attaches students to lessons
        
        :param timetables: dictionary of timetables with object of owner
        :type timetables: dict[webuntis.objects.StudentObject | webuntis.objects.KlassenObject, webuntis.objects.PeriodList]
        :param log_progress: wheter to print progressbar
        :type log_progress: bool
        :return: filtered lessons
        :rtype: PeriodList
        """
        if self.log:
            print("\nProcessing data...\n")

        lessons_by_obj: dict[webuntis.objects.PeriodObject, webuntis.objects.PeriodObject] = {}

        length = sum(len(timetable) for timetable in timetables.values())
        start_processing = time.time()
        i = 0

        for student, timetable in timetables.items():
            for lesson in timetable:
                i += 1

                existing = lessons_by_obj.get(lesson)
                if existing is None:
                    setattr(lesson, "students", [student])
                    lessons_by_obj[lesson] = lesson
                else:
                    existing.students.append(student) # type: ignore

                if self.log:
                    progress = int(i / length * 100)
                    bar_length = 40
                    filled = int(bar_length * i / length)
                    bar = '█' * filled + '░' * (bar_length - filled)

                    print("\033[1A\033[2K", end="")
                    print(f"[{bar}] {progress}%", flush=True)

        if self.log:
            duration_processing = time.time() - start_processing
            print(f"Processing data completed in {duration_processing:.2f} s.")

        return webuntis.objects.PeriodList(list(lessons_by_obj.values()), session=self.session)


    def cache_data(self, load_students: bool) -> None:
        """
        Caches timetable data with (every) lesson of everyone.

        Loads data with python-webuntis for every student. Filters duplications and adds student attachement for lessons (if load_students).

        Parameter
        ---------
        load_students: bool
            Whether to load the timetable for every student (else load them for every class).

        Returns
        -------
        lessons: webuntis.objects.PeriodList
            every lessons (with student attachement if load_students)
        """
        if load_students:
            timetables: dict[webuntis.objects.StudentObject | webuntis.objects.KlassenObject, webuntis.objects.PeriodList] = self._load_every_lesson_students()
            lessons: webuntis.objects.PeriodList = self._filter_lessons(timetables)
        else:
            timetables: dict[webuntis.objects.StudentObject | webuntis.objects.KlassenObject, webuntis.objects.PeriodList] = self._load_every_lesson_klassen()
            lessons: webuntis.objects.PeriodList = self._filter_lessons(timetables)
        
        self.cache = lessons
        return


    # identifier object handling
    def get_all_identifier(self, category: str) -> webuntis.objects.TeacherList | webuntis.objects.KlassenList | webuntis.objects.RoomList | webuntis.objects.StudentsList | list[str]:
        """
        Get every identifier possible in a category.

        Returns a list of students, classes, rooms or teachers.

        Parameter
        ---------
        category: str ("teacher", "klasse", "room", "student")
            Category of the Identifier
        
        Returns
        -------
        identifier: webuntis.objects.TeacherObject | webuntis.objects.KlassenObject | webuntis.objects.RoomObject | webuntis.objects.StudentObject
            Object for get_timetable() definig which timetable is returned
        """
        
        identifier = []

        if category == "teacher":
            identifier = self.session.teachers()
        elif category == "klasse":
            identifier = self.session.klassen()
        elif category == "room":
            identifier = self.session.rooms()
        elif category == "student":
            identifier = self.session.students()
        elif category == "mine":
            identifier = ["User"]
        else:
            raise ValueError('Invalid Value for "type". Expected: "teacher", "klasse", "room", "student".')
    
        return identifier


    def get_identifier_by_id_or_name(self, category: str, id_or_name: str) -> webuntis.objects.TeacherObject | webuntis.objects.KlassenObject | webuntis.objects.RoomObject | webuntis.objects.StudentObject | str | None:
        """
        Get identifier object by id or name.

        Returns a object for get_timetable() that matches name or id in a category.

        Parameter
        ---------
        category: str ("teacher", "klasse", "room", "student", "mine")
            Category of the Identifier
        id_or_name: str
            Id or Name of the Identifier
        
        Returns
        -------
        identifier: webuntis.objects.TeacherObject | webuntis.objects.KlassenObject | webuntis.objects.RoomObject | webuntis.objects.StudentObject | None
            Object of the Identifier for get_timetable()
        """

        all_elements = self.get_all_identifier(category)
        if category == "mine":
            return "User"
        else:
            for element in all_elements:
                try:
                    if element.id == int(id_or_name): # type:ignore
                        return element
                except:
                    pass
                    
                if getattr(element, "name", None):
                    if element.name == id_or_name: # type:ignore
                        return element
                if getattr(element, "long_name", None):
                    if element.long_name == id_or_name: # type:ignore
                        return element
                if getattr(element, "full_name", None):
                    if element.full_name == id_or_name: # type:ignore
                        return element
                if getattr(element, "title", None):
                    if element.title == id_or_name: # type:ignore
                        return element
                if getattr(element, "key", None):
                    if element.key == id_or_name: # type:ignore
                        return element
        
        return None



    # timetables
    def _get_timetable_for_teacher(self, teacher: webuntis.objects.TeacherObject) -> webuntis.objects.PeriodList:
        """
        Requesting timetable of a teacher.

        Returns a list of lessons (timetable) from a teacher in a given period of time.

        Parameter
        ---------
        teacher: webuntis.objects.TeacherObject
            Object containig the teacher
        
        Returns
        -------
        timetable: webuntis.objects.PeriodList
            Timetable of the given teacher.
        """

        lessons: list[webuntis.objects.PeriodObject] = []
        if self.cache is None:
            self.cache_data(load_students = False)
        
        if self.cache:
            for lesson in self.cache:
                try:
                    for lesson_teacher in lesson.teachers:
                        if teacher.id == lesson_teacher.id:
                            if lesson not in lessons:
                                lessons.append(lesson)
                except Exception as e:
                    print("No teacher: ", e) if self.log else None
                    pass
                try:
                    for lesson_original_teacher in lesson.original_teachers:
                        if teacher.id == lesson_original_teacher.id:
                            lessons.append(lesson)
                except Exception as e:
                    print("No original teacher: ", e) if self.log else None
                    pass

        table = webuntis.objects.PeriodList(lessons, session=self.session)
        return table


    def _get_timetable_for_class(self, klasse: webuntis.objects.KlassenObject) -> webuntis.objects.PeriodList:
        """
        Requesting timetable of a Class.

        Returns a list of lessons (timetable) from a class in a given period of time.

        Parameter
        ---------
        klasse: webuntis.objects.KlassenObject
            Object containig the class
        
        Returns
        -------
        timetable: webuntis.objects.PeriodList
            Timetable of the given class.
        """

        if not self.cache:
            start, end = self.time_period
            table = self.session.timetable_extended(klasse=klasse , start=start, end=end) # type: ignore
        else:
            lessons: list[webuntis.objects.PeriodObject] = []
            cache_lessons = self.cache       
            for lesson in cache_lessons:
                try:
                    for lesson_klasse in lesson.klassen:
                        if klasse.id == lesson_klasse.id:
                            lessons.append(lesson)
                except Exception as e:
                    print("No Class: ", e) if self.log else None
                    pass

            table = webuntis.objects.PeriodList(lessons, session=self.session)
        return table


    def _get_timetable_for_room(self, room: webuntis.objects.RoomObject) -> webuntis.objects.PeriodList:
        """
        Requesting timetable of a room.

        Returns a list of lessons (timetable) from a room in a given period of time.

        Parameter
        ---------
        room: webuntis.objects.RoomObject
            Object containig the room
        
        Returns
        -------
        timetable: webuntis.objects.PeriodList
            Timetable of the given room.
        """

        lessons: list[webuntis.objects.PeriodObject] = []
        if self.cache is None:
            self.cache_data(load_students = False)
        
        if self.cache:
            for lesson in self.cache:
                try:
                    for lesson_room in lesson.rooms:
                        if room.id == lesson_room.id:
                            lessons.append(lesson)
                except Exception as e:
                    print("No room: ", e) if self.log else None
                    pass
                try:
                    for lesson_original_room in lesson.original_rooms:
                        if room.id == lesson_original_room.id:
                            lessons.append(lesson)
                except Exception as e:
                    print("No original room: ", e) if self.log else None
                    pass

        table = webuntis.objects.PeriodList(lessons, session=self.session)
        return table


    def _get_timetable_for_student(self, student: webuntis.objects.StudentObject) -> webuntis.objects.PeriodList:
        """
        Requesting timetable of a student.

        Returns a list of lessons (timetable) from a student in a given period of time.

        Parameter
        ---------
        student: webuntis.objects.StudentObject
            Object containing the student
 
        Returns
        -------
        timetable: webuntis.objects.PeriodList
            Timetable of the given student.
        """
        
        if self.cache is None:
            start, end = self.time_period
            table = self.session.timetable_extended(student=student, start=start, end=end) # type: ignore
            return table
        else:
            lessons: list[webuntis.objects.PeriodObject] = []
            cache_lessons = self.cache       
            for lesson in cache_lessons:
                try:
                    for lesson_student in lesson.students: # type: ignore
                        if student.id == lesson_student.id: # type: ignore
                            lessons.append(lesson)
                except Exception as e:
                    print("No Student: ", e) if self.log else None
                    pass
            if lessons == []: # if there are no student attachments
                start, end = self.time_period
                table = self.session.timetable_extended(student=student, start=start, end=end) # type: ignore
                return table
                
            table = webuntis.objects.PeriodList(lessons, session=self.session)
        return table  


    def _get_timetable_for_user(self)-> webuntis.objects.PeriodList:
        """
        Requesting timetable of the user.

        Returns a list of lessons (timetable) from the user in a given period of time.

        Returns
        -------
        timetable: webuntis.objects.PeriodList
            Timetable of the given student.
        """
        if self.cache is None:
            start, end = self.time_period
            table = self.session.my_timetable(start=start, end=end)
            return table
        else:
            lessons: list[webuntis.objects.PeriodObject] = []
            cache_lessons = self.cache
            user = str(self.session.login_result["personId"]) # type: ignore
            print(user) if self.log else None
                
            for lesson in cache_lessons:
                try:
                    for lesson_student in lesson.students: # type: ignore
                        if user == lesson_student.id: # type: ignore
                            lessons.append(lesson)
                except Exception as e:
                    print("No Student: ", e) if self.log else None
                    pass
            
            if lessons == []: # if classee where loaded without student attachments for lessons
                start, end = self.time_period
                table = self.session.my_timetable(start=start, end=end)
                return table
                
            table = webuntis.objects.PeriodList(lessons, session=self.session)
            return table
        

    def get_timetable(self, identifier: webuntis.objects.TeacherObject | webuntis.objects.KlassenObject | webuntis.objects.RoomObject | webuntis.objects.StudentObject | str) -> webuntis.objects.PeriodList:
        """
        Requesting timetable of some identifier.

        Returns a list of lessons (timetable) from students, classes, rooms or teachers in a given period of time.

        Parameter
        ---------
        identifier: webuntis.objects.TeacherObject | webuntis.objects.KlassenObject | webuntis.objects.RoomObject | webuntis.objects.StudentObject
            Object from get_all_elements() definig which timetable is returned
        
        Returns
        -------
        timetable: webuntis.objects.PeriodList
            Timetable of the given identifier.
        """

        timetable_data = {}           
        
        if isinstance(identifier, webuntis.objects.TeacherObject):
            timetable_data = self._get_timetable_for_teacher(identifier)
        elif isinstance(identifier, webuntis.objects.KlassenObject):
            timetable_data = self._get_timetable_for_class(identifier)
        elif isinstance(identifier, webuntis.objects.RoomObject):
            timetable_data = self._get_timetable_for_room(identifier)
        elif isinstance(identifier, webuntis.objects.StudentObject):
            timetable_data = self._get_timetable_for_student(identifier)
        elif identifier == "User":
            timetable_data = self._get_timetable_for_user()
        else:
            raise ValueError('Invalid value for "identifier". Expected type: "teacher", "klasse", "room", "student". (Use get_element_by_id_or_name())')
        
        return timetable_data
    

    # UI
    def display_timetable(self ,timetable: webuntis.objects.PeriodList):
        """
        Prints out the timetable.
        """

        lessons: list[webuntis.objects.PeriodObject] = []
        for lesson in timetable:
            lessons.append(lesson)
        lessons.sort(key=lambda l: (getattr(l, "start", None), getattr(l, "end", None)))
        
        for lesson in lessons:
            start = self._try_getattr(lesson, "start") # Start
            end = self._try_getattr(lesson, "end") # Ende
            type_ = self._try_getattr(lesson, "type") # Stundentyp
            subj = self._try_getattr(lesson, "subjects") # Fach
            teachers = self._try_getattr(lesson, "teachers") # Lehrer
            klassen = self._try_getattr(lesson, "klassen") # Klassen
            studentGroup = self._try_getattr(lesson, "studentGroup") # Schülergruppe
            rooms = self._try_getattr(lesson, "rooms") # Räume

            lstext = self._try_getattr(lesson, "lstext")
            lsnumber = self._try_getattr(lesson, "lsnumber") # Stundenummer
            original_rooms = self._try_getattr(lesson, "original_rooms") # Räume vor Vertretung
            original_teachers = self._try_getattr(lesson, "original_teachers") # Lehrer vor Vertretung
            substText = self._try_getattr(lesson, "substText") # "Vertretung ohne Lehrer"
            bkRemark = self._try_getattr(lesson, "bkRemark")
            bkText = self._try_getattr(lesson, "bkText")
            code = self._try_getattr(lesson, "code")
            flags = self._try_getattr(lesson, "flags")
            info = self._try_getattr(lesson, "info") # Vertretungstext
            # students = try_getattr(lesson, "students")

            print(f"\n{start}-{end} {type_}: {subj} | Klassen: {klassen} | Gruppe: {studentGroup} | Lehrer: {teachers} | Räume: {rooms} \
    | lsnumber: {lsnumber} | lstext: {lstext} | original_rooms: {original_rooms} | original_teachers: {original_teachers} | substText: {substText} \
    | bkRemark: {bkRemark} | bkText: {bkText} | code: {code} | flags: {flags} | info: {info}")
        
        return


    def display_identifier(self, identifier: webuntis.objects.TeacherList | webuntis.objects.KlassenList | webuntis.objects.RoomList | webuntis.objects.StudentsList | list[str]):
        """
        Prints out a list of identifier.
        """
        for element in identifier:
            if getattr(element, "_data", None):
                print(element._data) # type: ignore
            else:
                print(element)


if __name__ == "__main__":
    print("This is the WebuntisAPI. It is not meant to be run directly. Please use WebuntisCLI.py for a command line interface, use WebuntisGUI.py for a graphical interface or import WebuntisAPI.py in your own project.")
