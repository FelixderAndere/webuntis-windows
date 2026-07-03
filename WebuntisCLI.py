"""
WebuntisCLI is a webuntis timetable CLI based on WebuntisAPI and "python-webuntis" made for displaying every timetable of students, classes, rooms and teachers.

Functions
---------
class WebuntisCLI():
    def load_credentials(self) -> tuple[str, str, str, str]:   
        Loads credentials from a file named "config.txt" and returns them as a tuple (server, school, username, password).
    def ask_credentials(self) -> tuple[str, str, str, str]:
        Prompts the user to input credentials (server, school, username, password) and returns them as a tuple.
    def run(self):
        The main function that runs the CLI. It handles loading credentials, logging in, caching data

Version
-------
1.0.0
"""


try:
    from WebuntisAPI import WebuntisAPI
    import webuntis
    import webuntis.objects
except ImportError as e:
    raise ImportError(f'Error occurred while importing: {e}. Note: This CLI is based on WebuntisAPI and "python-webuntis" <pip install webuntis>')


class WebuntisCLI():
    """WebuntisCLI is a WebuntisAPI Terminal App based on "WebuntisAPI" and "python-webuntis" made for getting every timetable of students, classes, rooms and teachers."""
    
    def load_credentials(self) -> tuple[str, str, str, str]:   
        try:
            import json
            from pathlib import Path

            credentials_path = Path(__file__).with_name("credentials.json")
            with credentials_path.open(encoding="utf-8") as file:
                credentials = json.load(file)

            return (
                credentials["server"],
                credentials["school"],
                credentials["username"],
                credentials["password"],
            )
        except Exception as e:
            print("Error: loading credentials from file (credentials.json)", e)
            exit(1)


    def ask_credentials(self) -> tuple[str, str, str, str]:
        server = input("Server: ")
        school = input("School: ")
        username = input("Username: ")
        password = input("Password: ")
        return server, school, username, password
    

    def run(self):
        # get credentials
        if input("load credentials from file credentials.json (Yes, No): ").lower() == "yes":
            server, school, username, password = self.load_credentials()
        else:
            server, school, username, password = self.ask_credentials()
        print(server, school, username, password)
        
        # login
        api: WebuntisAPI = WebuntisAPI(server=server, school=school, username=username, password=password, log=True)
        
        # cache timetables
        if input("cache? (Yes, No): ").lower() == "yes":
            load_students: bool = True if input("load all timetables for students? (Yes, No): ").lower() == "yes" else False
            api.cache_data(load_students=load_students)

        while True:
            # choose timetable owner
            category: str = input('category ("teacher", "klasse", "room", "student", "mine"): ')
            identifiers: webuntis.objects.TeacherList | webuntis.objects.KlassenList | webuntis.objects.RoomList | webuntis.objects.StudentsList | list[str] = api.get_all_identifier(category)
            api.display_identifier(identifiers)
            id_or_name: str = input("id or name: ")
            identifier: webuntis.objects.TeacherObject | webuntis.objects.KlassenObject | webuntis.objects.RoomObject | webuntis.objects.StudentObject | str | None = api.get_identifier_by_id_or_name(category, id_or_name)
            
            # get timetable for owner and display
            if identifier:
                timetable = api.get_timetable(identifier)
                api.display_timetable(timetable)
            else:
                print("No matching object found...")


if __name__ == "__main__":
    cli = WebuntisCLI()
    cli.run()
