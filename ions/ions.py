from .session import IonsSession


class Ions:
    def __init__(self, username="", password="", session=None):
        self.session = session or IonsSession(username, password)

    def get_reservatorios(self):
        url = self.session.build_url("hidrologia", "reservatorios")
        response = self.session.get(url)
        return response.json()
