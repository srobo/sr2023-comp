import collections

POINTS_IN_ZONE = {
    'B': 3,
    'S': 12,
    'G': 30,
}

POINTS_IN_ROBOT = {
    x: y / 3 for x, y in POINTS_IN_ZONE.items()
}

# Tokens can be "in" more than one zone or more than one robot (though not
# both), so while we can't check the overall counts easily we can check some
# combinations.
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

        # Normalise whitespace upfront for consistency
        for info in self._teams_data.values():
            info['robot_tokens'] = info['robot_tokens'].replace(" ", "")

        for info in self._arena_data.values():
            info['tokens'] = info['tokens'].replace(" ", "")

    def calculate_scores(self):
        scores = {}

        for tla, info in self._teams_data.items():
            robot_tokens = info['robot_tokens']
            zone_tokens = self._arena_data[info['zone']]['tokens']

            points = sum(POINTS_IN_ZONE[x] for x in zone_tokens)
            points += sum(POINTS_IN_ROBOT[x] for x in robot_tokens)

            if info.get('left_scoring_zone', False):
                points += 1

            scores[tla] = points

        return scores

    def validate(self, other_data):
        robot_token_inputs = {
            f'robot-{tla}': info['robot_tokens']
            for tla, info in self._teams_data.items()
        }
        zone_token_inputs = {
            f'zone-{zone}': info['tokens']
            for zone, info in self._arena_data.items()
        }
        all_inputs = {**robot_token_inputs, **zone_token_inputs}
        all_tokens = "".join(all_inputs.values())

        extra = set(all_tokens) - set(POINTS_IN_ZONE.keys())
        if extra:
            raise InvalidScoresheetException(
                f"Invalid token type: {extra!r}. "
                f"Must be one of: {', '.join(POINTS_IN_ZONE.keys())}",
            )

        # Assume that tokens won't leave the arena (that happening is less
        # likely than inputting the wrong numbers).
        token_counts = collections.Counter(all_tokens)
        for token_type, min_count in TOKEN_COUNTS.items():
            count = token_counts[token_type]
            if count < min_count:
                raise InvalidScoresheetException(
                    f"Too few {token_type} tokens seen. "
                    f"Must be at least {min_count} got {count}",
                )

        for name, tokens in all_inputs.items():
            token_counts = collections.Counter(tokens)
            for token_type, max_count in TOKEN_COUNTS.items():
                count = token_counts[token_type]
                if count > max_count:
                    raise InvalidScoresheetException(
                        f"Too many {token_type} tokens seen in {name}. "
                        f"Must be at most {max_count} got {count}",
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

        missing_but_has_token_teams = [
            tla
            for tla, info in self._teams_data.items()
            if info['robot_tokens']
            if not info.get('present', True)
        ]

        if missing_but_has_token_teams:
            raise InvalidScoresheetException(
                f"Teams {', '.join(missing_but_has_token_teams)} are not present "
                "but are marked as having tokens in the robot",
            )


if __name__ == '__main__':
    import libproton
    libproton.main(Scorer)
