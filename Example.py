try:
    from WebuntisCLI import WebuntisCLI
    from WebuntisGUI import WebuntisGUI
except ImportError as e:
    raise ImportError(f'Error occurred while importing: {e}. Note: This API is based on "python-webuntis" <pip install webuntis>')


if __name__ == "__main__":
    if input("Run GUI? (Y/n): ") == "Y":
        client = WebuntisGUI()
        client.run()

    else:
        client = WebuntisCLI()
        client.run()
