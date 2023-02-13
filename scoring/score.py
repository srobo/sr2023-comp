import collections

POINTS_IN_ZONE = {
    'B': 3,
    'S': 12,
    'G': 30,
}

POINTS_IN_ROBOT = {
    x: y / 3 for x, y in POINTS_IN_ZONE.items()
}

# Tokens can be "in" more than one zone, so we'll only check the minimum counts.
TOKEN_COUNTS = {
    'B': 20,
    'S': 12,
    'G': 4,
}


class InvalidScoresheetException(Exception):
    pass


class Scorer:
    def __init__(self, teams_data, arena_data):
        self._teams_data = teams_data
        self._arena_data = arena_data

    def calculate_scores(self):
        scores = {}

        for tla, info in self._teams_data.items():
            robot_tokens = info['robot_tokens']
            zone_tokens = self._arena_data[info['zone']]['tokens']

            points = sum(POINTS_IN_ZONE[y]
                         for x in zone_tokens if (y := x.strip()))
            points += sum(POINTS_IN_ROBOT[y]
                          for x in robot_tokens if (y := x.strip()))

            if info.get('left_scoring_zone', False):
                points += 1

            scores[tla] = points

        return scores

    def validate(self, other_data):
        robot_tokens = "".join(
            info['robot_tokens'] for info in self._teams_data.values()
        )
        zone_tokens = "".join(
            info['tokens'] for info in self._arena_data.values()
        )
        tokens = (robot_tokens + zone_tokens).replace(" ", "")

        extra = set(tokens) - set(POINTS_IN_ZONE.keys())
        if extra:
            raise InvalidScoresheetException(
                f"Invalid can state: {extra!r}. "
                f"Must be one of: {', '.join(POINTS_IN_ZONE.keys())}",
            )

        # Assume that tokens won't leave the arena (that happening is less
        # likely than inputting the wrong numbers).
        token_counts = collections.Counter(tokens)
        for token_type, min_count in TOKEN_COUNTS.items():
            count = token_counts[token_type]
            if count < min_count:
                raise InvalidScoresheetException(
                    f"Too few {token_type} tokens seen. "
                    f"Must be at least {min_count} got {count}",
                )

        missing_but_moving_teams = [
            tla
            for tla, info in self._teams_data.items()
            if info.get('left_scoring_zone', False)
            if not info.get('present', True)
        ]

        if missing_but_moving_teams:
            raise InvalidScoresheetException(
                f"Teams {', '.join(missing_but_moving_teams)} are not present "
                "but are marked as leaving their zone",
            )


if __name__ == '__main__':
    import libproton
    libproton.main(Scorer)
