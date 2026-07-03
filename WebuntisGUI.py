"""
WebuntisGUI is a webuntis timetable GUI based on WebuntisAPI and "python-webuntis" made for displaying every timetable of students, classes, rooms and teachers.

Functions
---------
class WebuntisGUI():
    def run(self):
        The main function that runs the GUI. It handles loading credentials, logging in, caching data, and displaying the timetable in a graphical interface.

Version
-------
1.2.0

TODO:
- Add option to load every timtable from every student

"""


try:
    from WebuntisAPI import WebuntisAPI
    import webuntis
    import webuntis.objects
    import datetime
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    from typing import Optional
    import threading
    import os
    import sys
    import json
except ImportError as e:
    raise ImportError(f'Error occurred while importing: {e}. Note: This GUI is based on WebuntisAPI and "python-webuntis" <pip install webuntis>')


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)


class WebuntisGUI():

    # Time slot configuration
    START_HOUR = 8
    END_HOUR = 18
    HOURS_PER_DAY = END_HOUR - START_HOUR
    
    WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    
    # Canvas dimensions (will be calculated dynamically)
    HOUR_HEIGHT = 70
    HEADER_HEIGHT = 45
    SIDEBAR_WIDTH = 70


    def __init__(self):
        """
        Initialize the GUI.
        
        Parameters
        ----------
        session : Session
            Authenticated Webuntis session from WebuntisAPI.login()
        """

        self.current_timetable = None
        self.current_identifier = None
        self.current_category = "klasse"
        self.lessons_by_day = {}
        self.selected_lesson = None
      

    class TimetableColors():
        """Color scheme for timetable display."""
        # Lesson backgrounds by type
        LESSON = "#E3F2FD"
        EXAMINATION = "#FFEBEE"
        BREAK = "#F5F5F5"
        FREE = "#FAFAFA"
        
        # Status colors
        SUBSTITUTION = "#FFF3E0"
        CANCELLED = "#FFCDD2"
        CURRENT_TIME = "#EF5350"
        
        # Text
        TEXT_PRIMARY = "#1A1A1A"
        TEXT_SECONDARY = "#666666"
        BORDER = "#E0E0E0"
        HEADER_BG = "#1565C0"
        HEADER_FG = "#FFFFFF"


    class Lesson(TimetableColors):
        """Wrapper for lesson data with display formatting."""
        
        def __init__(self, period_obj: webuntis.objects.PeriodObject, TimetableColors):
            self.TimetableColors = TimetableColors
            self.obj = period_obj
            self.start = self._get_attr("start")
            self.end = self._get_attr("end")
            self.subjects = self._get_attr("subjects")
            self.teachers = self._get_attr("teachers")
            self.klassen = self._get_attr("klassen")
            self.rooms = self._get_attr("rooms")
            self.type_ = self._get_attr("type")
            self.info = self._get_attr("info")
            self.code = self._get_attr("code")
            self.substText = self._get_attr("substText")
        
        def _get_attr(self, attr: str):
            """Try to get attribute of object (Needed because of "bugs" in python-webuntis...)"""
            try:
                return getattr(self.obj, attr, None)
            except Exception:
                return None
        
        def get_display_text(self) -> str:
            """Format lesson for display on canvas."""
            subj_text = str(self.subjects[0].name) if self.subjects else "N/A"
            time_text = f"{self._format_time(self.start)}"
            return f"{time_text}\n{subj_text}"
        
        @staticmethod
        def _format_time(time_val: Optional[int]) -> str:
            if not time_val:
                return "--:--"
            # Handle both datetime objects and HHMM integers
            if isinstance(time_val, datetime.datetime):
                return time_val.strftime("%H:%M")
            if isinstance(time_val, datetime.time):
                return time_val.strftime("%H:%M")
            hours = time_val // 100
            minutes = time_val % 100
            return f"{hours:02d}:{minutes:02d}"
        
        def get_color(self) -> str:
            """Determine lesson color based on type and status."""
            if self.code == "cancelled":
                return self.TimetableColors.CANCELLED
            if self.substText:
                return self.TimetableColors.SUBSTITUTION
            if self.type_ == "EXAMINATION":
                return self.TimetableColors.EXAMINATION
            return self.TimetableColors.LESSON
        
        def get_details(self) -> str:
            """Format full lesson details for popup."""
            lines = [
                f"Time: {self._format_time(self.start)} - {self._format_time(self.end)}",
                f"Subject: {self._format_subject_list(self.subjects)}",
                f"Teachers: {self._format_name_list(self.teachers)}",
                f"Classes: {self._format_name_list(self.klassen)}",
                f"Rooms: {self._format_name_list(self.rooms)}",
                f"Type: {self.type_ or 'N/A'}",
            ]
            if self.info:
                lines.append(f"Info: {self.info}")
            if self.substText:
                lines.append(f"Substitution: {self.substText}")
            return "\n".join(lines)
        
        @staticmethod
        def _format_subject_list(subjects) -> str:
            if not subjects:
                return "N/A"
            return ", ".join(str(s.name) for s in subjects)
        
        @staticmethod
        def _format_name_list(items) -> str:
            if not items:
                return "N/A"
            return ", ".join(str(item.name) for item in items)


    class CredentialsDialog:
        def __init__(self):
            self.result = None

            self.root = tk.Tk()
            self.root.title("Anmeldedaten")
            self.root.iconbitmap(resource_path("icon.ico"))

            self.entries = {}

            fields = ["server", "school", "username", "password"]

            for row, field in enumerate(fields):
                tk.Label(self.root, text=field.capitalize() + ":").grid(
                    row=row, column=0, padx=5, pady=5, sticky="w"
                )

                show = "*" if field == "password" else ""

                entry = tk.Entry(self.root, width=40, show=show)
                entry.grid(row=row, column=1, padx=5, pady=5)

                self.entries[field] = entry

            button_frame = tk.Frame(self.root)
            button_frame.grid(row=len(fields), column=0, columnspan=2, pady=10)

            tk.Button(
                button_frame,
                text="Laden",
                command=self.load_from_file
            ).pack(side="left", padx=5)

            tk.Button(
                button_frame,
                text="Speichern",
                command=self.save_to_file
            ).pack(side="left", padx=5)

            tk.Button(
                button_frame,
                text="OK",
                command=self.submit
            ).pack(side="left", padx=5)

            tk.Button(
                button_frame,
                text="Abbrechen",
                command=self.cancel
            ).pack(side="left", padx=5)

        def get_values(self):
            return {
                key: entry.get()
                for key, entry in self.entries.items()
            }


        def load_from_file(self):
            filename = filedialog.askopenfilename(
                filetypes=[("JSON-Dateien", "*.json")]
            )

            if not filename:
                return

            try:
                with open(filename, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for key, entry in self.entries.items():
                    entry.delete(0, tk.END)
                    entry.insert(0, data.get(key, ""))

            except Exception as e:
                messagebox.showerror(
                    "Fehler",
                    f"Datei konnte nicht geladen werden:\n{e}"
                )


        def save_to_file(self):
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                initialfile="credentials.json",
                filetypes=[("JSON-Dateien", "*.json")]
            )

            if not filename:
                return

            try:
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(
                        self.get_values(),
                        f,
                        indent=4,
                        ensure_ascii=False
                    )

            except Exception as e:
                messagebox.showerror(
                    "Fehler",
                    f"Datei konnte nicht gespeichert werden:\n{e}"
                )


        def submit(self):
            self.result = self.get_values()
            self.root.destroy()


        def cancel(self):
            self.result = None
            self.root.destroy()


        def show(self):
            self.root.mainloop()
            return self.result


    # Control panel
    def _setup_control_panel(self, parent):
        """Setup left control panel."""
        panel = ttk.Frame(parent, width=200)
        panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=5)
        
        # Category selection
        ttk.Label(panel, text="Category:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.category_var = tk.StringVar(value="klasse")
        category_frame = ttk.Frame(panel)
        category_frame.pack(fill=tk.X, pady=(0, 10))
        
        for category in ["mine", "klasse", "teacher", "room", "student"]:
            ttk.Radiobutton(
                category_frame,
                text=category.capitalize(),
                variable=self.category_var,
                value=category,
                command=self._on_category_changed
            ).pack(anchor=tk.W)
        
        # Identifier selection
        ttk.Label(panel, text="Select Identifier:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
        
        search_frame = ttk.Frame(panel)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(fill=tk.X)
        self.search_entry.bind("<Return>", lambda e: self._on_search())
        
        ttk.Button(search_frame, text="Search", command=self._on_search).pack(fill=tk.X, pady=(5, 0))
        
        # Identifier listbox
        ttk.Label(panel, text="Available:", font=("Arial", 9)).pack(anchor=tk.W, pady=(10, 5))
        
        listbox_frame = ttk.Frame(panel)
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.identifier_listbox = tk.Listbox(listbox_frame, height=12)
        self.identifier_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.identifier_listbox.bind("<<ListboxSelect>>", self._on_identifier_selected)
        
        # Scrollbar for listbox
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.identifier_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.identifier_listbox.config(yscrollcommand=scrollbar.set)
        
        # Load button
        ttk.Button(panel, text="Load Timetable", command=self._on_load_timetable).pack(fill=tk.X, pady=(0, 10))
        
        # Week navigation
        ttk.Label(panel, text="Navigation:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
        nav_frame = ttk.Frame(panel)
        nav_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(nav_frame, text="← Prev", command=self._previous_week).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        ttk.Button(nav_frame, text="Today", command=self._current_week).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        ttk.Button(nav_frame, text="Next →", command=self._next_week).pack(side=tk.LEFT, fill=tk.X)
        
        # Load initial identifiers
        self._load_identifiers()
    

    def _load_identifiers(self):
        """Load identifiers for current category into listbox."""
        self.identifier_listbox.delete(0, tk.END)
        self.root.update()
        
        try:
            category = self.category_var.get()
            
            # Special handling for "mine" category
            if category == "mine":
                self.identifier_listbox.insert(tk.END, "Your Timetable")
                self.current_identifier = "mine"
                return
            
            identifiers = self.api.get_all_identifier(category)
            
            for identifier in identifiers:
                name = getattr(identifier, "name", str(identifier))
                self.identifier_listbox.insert(tk.END, name)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load identifiers: {e}")
    

    def _on_category_changed(self):
        """Handle category selection change."""
        self._load_identifiers()
    

    def _on_search(self):
        """Filter listbox based on search input."""
        search_text = self.search_var.get().lower()
        if not search_text:
            self._load_identifiers()
            return
        
        self.identifier_listbox.delete(0, tk.END)
        category = self.category_var.get()
        try:
            identifiers = self.api.get_all_identifier(category)
            
            for identifier in identifiers:
                name = getattr(identifier, "name", str(identifier))
                if search_text in name.lower():
                    self.identifier_listbox.insert(tk.END, name)
            
            self.status_var.set(f"Found {self.identifier_listbox.size()} results")
        except Exception as e:
            messagebox.showerror("Error", f"Search failed: {e}")
    

    def _on_identifier_selected(self, event):
        """Handle identifier selection from listbox."""
        selection = self.identifier_listbox.curselection()
        if selection:
            self.current_identifier = self.identifier_listbox.get(selection[0])
    

    def _previous_week(self):
        """Navigate to previous week."""
        start, end = self.current_week
        self.current_week = (
            start - datetime.timedelta(days=7),
            end - datetime.timedelta(days=7)
        )
        self.api.time_period = self.current_week
        
        self._on_load_timetable()
        self._update_week_display()


    def _next_week(self):
        """Navigate to next week."""
        start, end = self.current_week
        self.current_week = (
            start + datetime.timedelta(days=7),
            end + datetime.timedelta(days=7)
        )
        self.api.time_period = self.current_week
        
        self._on_load_timetable()
        self._update_week_display()


    def _current_week(self):
        """Jump to current week."""
        self.current_week = self.api._get_current_week()
        self.api.time_period = self.current_week

        self._on_load_timetable()
        self._update_week_display()


    # Timetable
    def _setup_timetable_canvas(self, parent):
        """Setup timetable canvas on right."""
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        # Canvas with scrollbars
        self.canvas = tk.Canvas(
            canvas_frame,
            bg=self.TimetableColors.FREE,
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready. Select an identifier and click 'Load Timetable'")
        status_bar = ttk.Label(canvas_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, pady=(5, 0))
    

    def _on_load_timetable(self):
        """Load timetable for selected identifier."""
        if not self.current_identifier:
            messagebox.showwarning("Warning", "Please select an identifier first")
            return

        self.status_var.set(f"Loading timetable for {self.current_identifier}...")
        self.root.update()

        def load_in_thread():
            try:
                category = self.category_var.get()
                identifier = self.api.get_identifier_by_id_or_name(category, str(self.current_identifier))
                if not identifier:
                    raise ValueError(f"Identifier '{self.current_identifier}' not found")
                
                self.api.cache = None  # Clear cache to ensure fresh data
                timetable = self.api.get_timetable(identifier)
                self.current_timetable = timetable
                self._render_timetable()
                self.status_var.set(f"Loaded {len(timetable)} lessons")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load timetable: {e}")
                self.status_var.set("Error loading timetable")
        
        thread = threading.Thread(target=load_in_thread, daemon=True)
        thread.start()
    

    def _render_timetable(self):
        """Render timetable on canvas."""
        if not self.current_timetable:
            return
        
        # Clear canvas
        self.canvas.delete("all")
        
        # Organize lessons by day
        self.lessons_by_day = self._organize_lessons_by_day()
        
        # Calculate dynamic HOUR_WIDTH based on canvas width
        canvas_width = self.canvas.winfo_width()
        if canvas_width <= 1:
            canvas_width = 800  # Fallback for initial render
        
        available_width = canvas_width - self.SIDEBAR_WIDTH
        self.HOUR_WIDTH = max(100, available_width // len(self.WEEKDAYS))
        
        # Calculate canvas size
        calc_canvas_width = self.SIDEBAR_WIDTH + (len(self.WEEKDAYS) * self.HOUR_WIDTH)
        calc_canvas_height = self.HEADER_HEIGHT + (self.HOURS_PER_DAY * self.HOUR_HEIGHT)
        
        self.canvas.config(scrollregion=(0, 0, calc_canvas_width, calc_canvas_height))
        
        # Draw header (time labels)
        self._draw_time_header()
        
        # Draw grid
        self._draw_grid()
        
        # Draw lessons
        self._draw_lessons()
        
        # Draw day headers last (on top) so they don't get covered
        self._draw_day_headers()
    

    def _organize_lessons_by_day(self) -> dict:
        """Organize lessons by weekday."""
        lessons_by_day = {day: [] for day in self.WEEKDAYS}
        start_date, end_date = self.current_week
        
        if not self.current_timetable:
            return lessons_by_day
        else:
            for period in self.current_timetable:
                lesson = self.Lesson(period, self.TimetableColors)
                if not lesson.start:
                    continue
                
                # Extract date from the start datetime/time object
                try:
                    lesson_date = None
                    # If start is a datetime object, extract the date
                    if isinstance(lesson.start, datetime.datetime):
                        lesson_date = lesson.start.date()
                    elif isinstance(lesson.start, datetime.date):
                        lesson_date = lesson.start
                    else:
                        # If it's an integer (HHMM format), we need another approach
                        # Try to get date from period object directly
                        period_date = getattr(period, 'date', None)
                        if period_date:
                            if isinstance(period_date, int):
                                year = period_date // 10000
                                month = (period_date % 10000) // 100
                                day = period_date % 100
                                lesson_date = datetime.date(year, month, day)
                            elif isinstance(period_date, datetime.date):
                                lesson_date = period_date
                            else:
                                lesson_date = None
                        
                        if not lesson_date:
                            lesson_date = start_date
                            
                except Exception as e:
                    lesson_date = start_date
                
                # Ensure lesson_date is set
                if not lesson_date:
                    lesson_date = start_date
                
                # Determine weekday name - only add if within current week
                if start_date <= lesson_date <= end_date:
                    day_name = self.WEEKDAYS[lesson_date.weekday()]
                    lessons_by_day[day_name].append(lesson)
            
            # Sort lessons by start time
            for day in lessons_by_day:
                lessons_by_day[day].sort(key=lambda l: l.start or 0)
            
            return lessons_by_day
    

    def _get_lesson_date(self, start_time: int) -> Optional[datetime.date]:
        """Determine which date a lesson belongs to."""
        # Start time format: HHMM (e.g., 0800 for 8:00)
        # We'll use the current week and determine which day based on lesson time
        # For now, assume lessons are distributed across the week
        start_date, end_date = self.current_week
        
        # Simple heuristic: lessons on the week of start_date
        # In a real app, the API might provide the date directly
        return start_date
    

    def _draw_time_header(self):
        """Draw time labels on left sidebar with modern styling."""
        # Draw sidebar background
        self.canvas.create_rectangle(
            0, self.HEADER_HEIGHT,
            self.SIDEBAR_WIDTH, self.HEADER_HEIGHT + self.HOURS_PER_DAY * self.HOUR_HEIGHT,
            fill="#F5F5F5",
            outline=self.TimetableColors.BORDER,
            width=1
        )
        
        y_offset = self.HEADER_HEIGHT
        
        for hour in range(self.START_HOUR, self.END_HOUR + 1):
            time_text = f"{hour:02d}:00"
            y_pos = y_offset + (hour - self.START_HOUR) * self.HOUR_HEIGHT
            
            self.canvas.create_text(
                self.SIDEBAR_WIDTH / 2,
                y_pos + self.HOUR_HEIGHT / 2,
                text=time_text,
                font=("Arial", 9, "bold"),
                fill=self.TimetableColors.TEXT_SECONDARY
            )
    

    def _format_week_label(self) -> str:
        """Format week display label."""
        start, end = self.current_week
        return f"Week {start.isocalendar()[1]}: {start.strftime('%d.%m')} - {end.strftime('%d.%m.%Y')}"
    

    def _update_week_display(self):
        """Update week label and refresh timetable if loaded."""
        self.week_label.config(text=self._format_week_label())
        if self.current_timetable:
            self._on_load_timetable()


    def _draw_day_headers(self):
        """Draw weekday headers with modern styling."""
        start_date, _ = self.current_week
        
        for i, day in enumerate(self.WEEKDAYS):
            x = self.SIDEBAR_WIDTH + i * self.HOUR_WIDTH
            
            # Calculate actual date
            day_date = start_date + datetime.timedelta(days=i)
            date_str = day_date.strftime("%d.%m")
            
            # Background
            self.canvas.create_rectangle(
                x, 0,
                x + self.HOUR_WIDTH, self.HEADER_HEIGHT,
                fill=self.TimetableColors.HEADER_BG,
                outline=self.TimetableColors.BORDER,
                width=1
            )
            
            # Day name
            self.canvas.create_text(
                x + self.HOUR_WIDTH / 2, self.HEADER_HEIGHT / 3,
                text=day,
                font=("Arial", 10, "bold"),
                fill=self.TimetableColors.HEADER_FG
            )
            
            # Date
            self.canvas.create_text(
                x + self.HOUR_WIDTH / 2, 2 * self.HEADER_HEIGHT / 3,
                text=date_str,
                font=("Arial", 8),
                fill=self.TimetableColors.HEADER_FG
            )
    

    def _draw_grid(self):
        """Draw grid lines with modern styling."""
        # Vertical lines (days)
        for i in range(len(self.WEEKDAYS) + 1):
            x = self.SIDEBAR_WIDTH + i * self.HOUR_WIDTH
            self.canvas.create_line(
                x, self.HEADER_HEIGHT,
                x, self.HEADER_HEIGHT + self.HOURS_PER_DAY * self.HOUR_HEIGHT,
                fill=self.TimetableColors.BORDER,
                width=1
            )
        
        # Horizontal lines (hours) - slightly different styling
        for hour in range(self.HOURS_PER_DAY + 1):
            y = self.HEADER_HEIGHT + hour * self.HOUR_HEIGHT
            self.canvas.create_line(
                0, y,
                self.SIDEBAR_WIDTH + len(self.WEEKDAYS) * self.HOUR_WIDTH, y,
                fill=self.TimetableColors.BORDER,
                width=1 if hour % 2 == 0 else 1
            )
    

    # Lessons:
    def _draw_lessons(self):
        """Draw all lessons as single boxes without splitting a lesson."""
        self._lesson_item_map = {}

        for day_idx, day in enumerate(self.WEEKDAYS):
            lessons = self.lessons_by_day.get(day, [])
            if not lessons:
                continue

            layout = self._layout_day_lessons(lessons)
            for lesson, (col, total_cols) in layout.items():
                self._draw_lesson_box(day_idx, lesson, col, total_cols)


    def _layout_day_lessons(self, lessons: list) -> dict:
        """
        Assign each lesson a fixed column and a fixed total column count.

        Lessons are grouped into overlap components.
        Inside one component, each lesson gets one stable column.
        The total width is the maximum concurrency in that component.
        """
        # Keep only lessons with usable times
        normalized = []
        for lesson in lessons:
            s = self._lesson_time_to_minutes(lesson.start)
            e = self._lesson_time_to_minutes(lesson.end)
            if s is None or e is None or e <= s:
                continue
            normalized.append((lesson, s, e))

        if not normalized:
            return {}

        # Split into overlap components
        components = []
        remaining = normalized[:]

        while remaining:
            seed = remaining.pop(0)
            component = [seed]
            queue = [seed]

            while queue:
                current_lesson, _, _ = queue.pop(0)

                for item in remaining[:]:
                    other_lesson, _, _ = item
                    if self._lessons_overlap(current_lesson, other_lesson):
                        remaining.remove(item)
                        component.append(item)
                        queue.append(item)

            components.append(component)

        layout = {}

        for component in components:
            # Greedy first-fit column assignment
            component.sort(key=lambda x: (x[1], x[2]))
            column_ends = []
            assignments = {}

            for lesson, start, end in component:
                placed = False
                for col_idx, col_end in enumerate(column_ends):
                    if start >= col_end:
                        column_ends[col_idx] = end
                        assignments[lesson] = col_idx
                        placed = True
                        break

                if not placed:
                    column_ends.append(end)
                    assignments[lesson] = len(column_ends) - 1

            total_cols = self._max_concurrent_lessons(component)
            total_cols = max(1, total_cols)

            for lesson, _, _ in component:
                layout[lesson] = (assignments[lesson], total_cols)

        return layout


    def _max_concurrent_lessons(self, component: list) -> int:
        """Return the maximum number of overlapping lessons in a component."""
        events = []
        for _, start, end in component:
            events.append((start, 1))
            events.append((end, -1))

        # End events first at the same minute
        events.sort(key=lambda x: (x[0], x[1]))

        active = 0
        max_active = 0
        for _, delta in events:
            active += delta
            if active > max_active:
                max_active = active

        return max_active


    def _draw_lesson_box(self, day_idx: int, lesson: "Lesson", col: int = 0, total_cols: int = 1):
        """Draw one lesson as a single rectangle."""
        if not lesson.start or not lesson.end:
            return

        start = self._lesson_time_to_minutes(lesson.start)
        end = self._lesson_time_to_minutes(lesson.end)
        if start is None or end is None or end <= start:
            return

        visible_start = self.START_HOUR * 60
        visible_end = self.END_HOUR * 60

        # Clip to visible range
        start = max(start, visible_start)
        end = min(end, visible_end)
        if end <= start:
            return

        start_offset = ((start - visible_start) / 60) * self.HOUR_HEIGHT
        end_offset = ((end - visible_start) / 60) * self.HOUR_HEIGHT
        duration = end_offset - start_offset

        day_x1 = self.SIDEBAR_WIDTH + day_idx * self.HOUR_WIDTH
        day_width = self.HOUR_WIDTH

        col_width = day_width / total_cols
        x1 = day_x1 + col * col_width + 2
        x2 = day_x1 + (col + 1) * col_width - 2

        y1 = self.HEADER_HEIGHT + start_offset + 2
        y2 = self.HEADER_HEIGHT + end_offset - 2

        if y2 - y1 < 20:
            y2 = y1 + 20

        # Shadow
        self.canvas.create_rectangle(
            x1 + 1, y1 + 1, x2 + 1, y2 + 1,
            fill="#E0E0E0",
            outline=""
        )

        color = lesson.get_color()
        box_id = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=color,
            outline="#1976D2",
            width=2
        )

        text = lesson.get_display_text()
        text_id = self.canvas.create_text(
            (x1 + x2) / 2,
            (y1 + y2) / 2,
            text=text,
            font=("Arial", 8, "bold"),
            fill=self.TimetableColors.TEXT_PRIMARY,
            justify=tk.CENTER
        )

        self._lesson_item_map[box_id] = lesson
        self._lesson_item_map[text_id] = lesson

        self.canvas.tag_bind(box_id, "<Button-1>", lambda e, l=lesson: self._show_lesson_details(l))
        self.canvas.tag_bind(text_id, "<Button-1>", lambda e, l=lesson: self._show_lesson_details(l))


    def _lesson_time_to_minutes(self, lesson_time):
        """Convert lesson time to minutes since midnight."""
        if lesson_time is None:
            return None

        if isinstance(lesson_time, datetime.datetime):
            return lesson_time.hour * 60 + lesson_time.minute

        if isinstance(lesson_time, datetime.time):
            return lesson_time.hour * 60 + lesson_time.minute

        try:
            hours = lesson_time // 100
            minutes = lesson_time % 100
            return hours * 60 + minutes
        except Exception:
            return None


    def _lessons_overlap(self, lesson1: "Lesson", lesson2: "Lesson") -> bool:
        """Check if two lessons overlap in time."""
        def get_time_minutes(lesson_time):
            if isinstance(lesson_time, datetime.datetime):
                return lesson_time.hour * 60 + lesson_time.minute
            if isinstance(lesson_time, datetime.time):
                return lesson_time.hour * 60 + lesson_time.minute
            return (lesson_time // 100) * 60 + (lesson_time % 100)

        start1 = get_time_minutes(lesson1.start)
        end1 = get_time_minutes(lesson1.end)
        start2 = get_time_minutes(lesson2.start)
        end2 = get_time_minutes(lesson2.end)

        return not (end1 <= start2 or end2 <= start1)


    def _minutes_to_canvas_y(self, minutes: int) -> float:
        """Convert minutes since midnight to canvas Y coordinate."""
        return self.HEADER_HEIGHT + ((minutes - self.START_HOUR * 60) / 60) * self.HOUR_HEIGHT


    def _draw_lesson_segment(
        self,
        lesson: "Lesson",
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        show_text: bool = False,
    ):
        """Draw one lesson segment."""
        if x2 <= x1 or y2 <= y1:
            return

        color = lesson.get_color()

        # Shadow
        self.canvas.create_rectangle(
            x1 + 1, y1 + 1, x2 + 1, y2 + 1,
            fill="#E0E0E0",
            outline="",
        )

        # Main box
        rect_id = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=color,
            outline="#1976D2",
            width=2,
        )

        # Store mapping for click lookup
        self._lesson_item_map[rect_id] = lesson

        # Text only on the largest segment of that lesson
        if show_text and (y2 - y1) >= 20 and (x2 - x1) >= 40:
            text_id = self.canvas.create_text(
                (x1 + x2) / 2,
                (y1 + y2) / 2,
                text=lesson.get_display_text(),
                font=("Arial", 8, "bold"),
                fill=self.TimetableColors.TEXT_PRIMARY,
                justify=tk.CENTER,
            )
            self._lesson_item_map[text_id] = lesson

     
    def _show_lesson_details(self, lesson: Lesson):
        """Show lesson details in popup."""
        details = lesson.get_details()
        messagebox.showinfo(f"Lesson Details", details)


    # main
    def _setup_ui(self):
        """Setup the user interface."""
        # Header frame
        self._setup_header()
        
        # Main content frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Control panel (left)
        self._setup_control_panel(main_frame)
        
        # Timetable canvas (right)
        self._setup_timetable_canvas(main_frame)
    
    
    def _setup_header(self):
        """Setup top header with title and week info."""
        header = tk.Frame(self.root, bg=self.TimetableColors.HEADER_BG, height=50)
        header.pack(fill=tk.X, padx=0, pady=0)
        header.pack_propagate(False)
        
        title = tk.Label(
            header,
            text="Webuntis Timetable Viewer",
            bg=self.TimetableColors.HEADER_BG,
            fg=self.TimetableColors.HEADER_FG,
            font=("Arial", 14, "bold")
        )
        title.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.week_label = tk.Label(
            header,
            text=self._format_week_label(),
            bg=self.TimetableColors.HEADER_BG,
            fg=self.TimetableColors.HEADER_FG,
            font=("Arial", 10)
        )
        self.week_label.pack(side=tk.RIGHT, padx=10, pady=10)


    def run(self):
        """Start the GUI event loop."""
        dialog = self.CredentialsDialog()
        credentials = dialog.show()

        if not credentials:
            messagebox.showinfo("Info", "No credentials provided. Exiting.")
            return
        self.api = WebuntisAPI(
            server=credentials["server"],
            school=credentials["school"],
            username=credentials["username"],
            password=credentials["password"],
            log=False
        )
        self.current_week = self.api._get_current_week()

        self.root = tk.Tk()
        self.root.title("Webuntis Timetable")
        self.root.geometry("1400x700")
        self.root.iconbitmap(resource_path("icon.ico"))
        self._setup_ui()
        self.root.mainloop()


if __name__ == "__main__":
    client = WebuntisGUI()
    client.run()
