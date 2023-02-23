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
    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


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

    def _max_counts(self, token_inputs):
        max_counts = collections.Counter()

        for tokens in token_inputs:
            counts = collections.Counter(tokens)
            for token_type in TOKEN_COUNTS.keys():
                if counts[token_type] > max_counts[token_type]:
                    max_counts[token_type] = counts[token_type]

        return max_counts

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
                code='invalid_token',
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
                    code='too_few_tokens',
                )

        for name, tokens in all_inputs.items():
            token_counts = collections.Counter(tokens)
            for token_type, max_count in TOKEN_COUNTS.items():
                count = token_counts[token_type]
                if count > max_count:
                    raise InvalidScoresheetException(
                        f"Too many {token_type} tokens seen in {name}. "
                        f"Must be at most {max_count} got {count}",
                        code='too_many_tokens',
                    )

        # While tokens can be shared between zones, they can't be shared between
        # a zone and a robot. We can therefore catch some cases where there are
        # too many tokens "overall", though with limited impact.
        max_robot_counts = self._max_counts(robot_token_inputs.values())
        max_zone_counts = self._max_counts(zone_token_inputs.values())
        total_counts = max_robot_counts + max_zone_counts

        for token_type, max_count in TOKEN_COUNTS.items():
            count = total_counts[token_type]
            if count > max_count:
                raise InvalidScoresheetException(
                    f"Too many {token_type} tokens seen overall. "
                    f"Must be at most {max_count} got {count}",
                    code='too_many_tokens_between_robots_and_zones',
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
                code='missing_but_moving',
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
                code='missing_but_has_tokens',
            )


if __name__ == '__main__':
    import libproton
    libproton.main(Scorer)
