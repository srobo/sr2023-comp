class InvalidScoresheetException(Exception):
    pass


class Scorer:
    def __init__(self, teams_data, arena_data):
        self._teams_data = teams_data
        self._arena_data = arena_data

    def calculate_scores(self):
        raise NotImplementedError


if __name__ == '__main__':
    import libproton
    libproton.main(Scorer)
