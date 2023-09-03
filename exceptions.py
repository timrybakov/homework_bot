class ConnectionException(Exception):
    """Исключение возникает из-за проблемы с соединением."""
    def __init__(self, message='Проблема подключения'):
        self.message = message
        super().__init__(self.message)


class TimeOutException(Exception):
    """Исключение возникает при долгой поппытке подключения."""
    def __init__(self, message='Время на подключение истекло'):
        self.message = message
        super().__init__(self.message)


class UnusualAPIException(Exception):
    """
    Исключение возникает при нестандартных
    ошибках при отправке запроса к API.
    """
    def __init__(
            self,
            message='Возникает при нестандартной ошибке при запросе к API'
    ):
        self.message = message
        super().__init__(self.message)