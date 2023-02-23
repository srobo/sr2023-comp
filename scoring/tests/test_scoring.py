#!/usr/bin/env python3

# Path hackery
import pathlib
import random
import sys
import unittest

import yaml

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from score import (  # noqa: E402
    InvalidScoresheetException,
    POINTS_IN_ROBOT,
    POINTS_IN_ZONE,
    Scorer,
    TOKEN_COUNTS,
)


def shuffled(text: str) -> str:
    values = list(text)
    random.shuffle(values)
    return ''.join(values)


class ScorerTests(unittest.TestCase):
    longMessage = True

    def construct_scorer(self, robot_contents, zone_tokens):
        return Scorer(
            {
                tla: {**info, 'robot_tokens': robot_contents.get(tla, "")}
                for tla, info in self.teams_data.items()
            },
            {x: {'tokens': y} for x, y in zone_tokens.items()},
        )

    def assertScores(self, expected_scores, robot_contents, zone_tokens):
        scorer = self.construct_scorer(robot_contents, zone_tokens)
        scorer.validate(None)
        actual_scores = scorer.calculate_scores()

        self.assertEqual(expected_scores, actual_scores, "Wrong scores")

    def assertInvalidScoresheet(self, robot_contents, zone_tokens, *, code):
        scorer = self.construct_scorer(robot_contents, zone_tokens)

        with self.assertRaises(InvalidScoresheetException) as cm:
            scorer.validate(None)

        self.assertEqual(
            code,
            cm.exception.code,
            f"Wrong error code, message was: {cm.exception}",
        )

    def setUp(self):
        self.teams_data = {
            'ABC': {'zone': 0, 'present': True, 'left_scoring_zone': False},
            'DEF': {'zone': 1, 'present': True, 'left_scoring_zone': False},
        }
        tokens_per_zone = 'B' * 5 + 'S' * 3 + 'G'
        self.zone_tokens = {
            0: shuffled(tokens_per_zone),
            1: shuffled(tokens_per_zone),
            2: shuffled(tokens_per_zone),
            3: shuffled(tokens_per_zone),
        }

    def test_consistent_keys(self):
        self.assertEqual(
            POINTS_IN_ZONE.keys(),
            TOKEN_COUNTS.keys(),
            "Token count keys don't match the points keys",
        )
        self.assertEqual(
            POINTS_IN_ZONE.keys(),
            POINTS_IN_ROBOT.keys(),
            "Points keys are inconsistent",
        )

    def test_template(self):
        template_path = ROOT / 'template.yaml'
        with template_path.open() as f:
            data = yaml.safe_load(f)

        teams_data = data['teams']
        arena_data = data.get('arena_zones')
        extra_data = data.get('other')

        scorer = Scorer(teams_data, arena_data)
        scores = scorer.calculate_scores()

        scorer.validate(extra_data)

        self.assertEqual(
            teams_data.keys(),
            scores.keys(),
            "Should return score values for every team",
        )

    # Scoring logic

    def test_default_token_positions(self):
        self.assertScores(
            {'ABC': 81, 'DEF': 81},
            {},
            self.zone_tokens,
        )

    def test_tokens_shared_several_zones(self):
        self.zone_tokens[0] += 'G'
        self.zone_tokens[2] += 'G'

        self.assertScores(
            {'ABC': 111, 'DEF': 81},
            {},
            self.zone_tokens,
        )

    def test_token_shared_two_robots(self):
        # The Gold token which was in zone 0
        self.zone_tokens[0] = self.zone_tokens[0].replace('G', '')

        # is actually being held by both ABC and DEF
        robot_tokens = {
            'ABC': 'G',
            'DEF': 'G',
        }

        self.assertScores(
            {'ABC': 61, 'DEF': 91},
            robot_tokens,
            self.zone_tokens,
        )

    def test_tokens_in_robot(self):
        self.zone_tokens[0] = 'B' * 4 + 'S' * 2
        self.assertScores(
            {'ABC': 51, 'DEF': 81},
            {'ABC': shuffled('BSG')},
            self.zone_tokens,
        )

    def test_left_scoring_zone(self):
        self.teams_data['ABC']['left_scoring_zone'] = True
        self.assertScores(
            {'ABC': 82, 'DEF': 81},
            {},
            self.zone_tokens,
        )

    def test_tokens_in_robot_and_left_scoring_zone(self):
        self.teams_data['ABC']['left_scoring_zone'] = True
        self.zone_tokens[0] = 'B' * 4 + 'S' * 2
        self.assertScores(
            {'ABC': 52, 'DEF': 81},
            {'ABC': shuffled('BSG')},
            self.zone_tokens,
        )

    # Invalid characters

    def test_invalid_zone_token_characters(self):
        self.zone_tokens[0] += 'X'
        self.assertInvalidScoresheet(
            {},
            self.zone_tokens,
            code='invalid_token',
        )

    def test_invalid_robot_token_characters(self):
        self.assertInvalidScoresheet(
            {'ABC': 'X'},
            self.zone_tokens,
            code='invalid_token',
        )

    def test_lower_case_zone_token_characters(self):
        self.zone_tokens[0] = 's'
        self.assertInvalidScoresheet(
            {},
            self.zone_tokens,
            code='invalid_token',
        )

    def test_lower_case_robot_token_characters(self):
        self.assertInvalidScoresheet(
            {'ABC': 's'},
            self.zone_tokens,
            code='invalid_token',
        )

    def test_invalid_zone_token_characters_in_zone_without_robot(self):
        self.zone_tokens[3] += 'X'
        self.assertInvalidScoresheet(
            {},
            self.zone_tokens,
            code='invalid_token',
        )

    def test_lower_case_zone_token_characters_in_zone_without_robot(self):
        self.zone_tokens[3] += 's'
        self.assertInvalidScoresheet(
            {},
            self.zone_tokens,
            code='invalid_token',
        )

    # Missing tokens

    def test_less_than_26_tokens_seen(self):
        self.zone_tokens[0] = 'S'
        self.assertInvalidScoresheet(
            {},
            self.zone_tokens,
            code='too_few_tokens',
        )

    def test_less_than_26_tokens_seen_in_zone_without_robot(self):
        self.zone_tokens[3] = 'S'
        self.assertInvalidScoresheet(
            {},
            self.zone_tokens,
            code='too_few_tokens',
        )

    # Extra tokens

    def test_too_many_tokens_single_zone(self):
        # Remove all the other gold tokens so it's clear what we're testing
        self.zone_tokens = {
            x: y.replace('G', '') for x, y in self.zone_tokens.items()
        }

        self.zone_tokens[0] += 'G' * 5
        self.assertInvalidScoresheet(
            {},
            self.zone_tokens,
            code='too_many_tokens',
        )

    def test_too_many_tokens_single_robot(self):
        self.assertInvalidScoresheet(
            {'ABC': 'S' * 13},
            self.zone_tokens,
            code='too_many_tokens',
        )

    def test_too_many_tokens_between_robots_and_zones(self):
        # 5 Silver tokens in robot ABC
        robot_tokens = {'ABC': 'S' * 6}
        self.assertScores(
            {'ABC': 105, 'DEF': 81},
            robot_tokens,
            self.zone_tokens,
        )

        # Total of 8 Silver tokens in zone 1
        self.zone_tokens[0] += 'SSSS'
        self.assertScores(
            {'ABC': 129, 'DEF': 81},
            {},
            self.zone_tokens,
        )

        # While allowed separately, this combination isn't possible together
        # (since tokens cannot be both in a zone and a robot).
        self.assertInvalidScoresheet(
            robot_tokens,
            self.zone_tokens,
            code='too_many_tokens_between_robots_and_zones',
        )

    # Tolerable input deviances

    def test_space_in_zone_tokens(self):
        self.zone_tokens[0] = shuffled(self.zone_tokens[0] + "      ")
        self.assertScores(
            {'ABC': 81, 'DEF': 81},
            {},
            self.zone_tokens,
        )

    def test_space_in_robot_tokens(self):
        self.zone_tokens[0] = 'B' * 4 + 'S' * 2
        self.assertScores(
            {'ABC': 51, 'DEF': 81},
            {'ABC': ' B  S G '},
            self.zone_tokens,
        )

    def test_left_scoring_zone_not_specified(self):
        self.teams_data = {
            'ABC': {'zone': 0, 'present': True},
            'DEF': {'zone': 1, 'present': True},
        }
        self.assertScores(
            {'ABC': 81, 'DEF': 81},
            {},
            self.zone_tokens,
        )

    # Impossible scenarios

    def test_left_scoring_zone_but_absent(self):
        self.teams_data = {
            'ABC': {'zone': 0, 'present': False, 'left_scoring_zone': True},
            'DEF': {'zone': 1, 'present': True, 'left_scoring_zone': False},
        }
        self.assertInvalidScoresheet(
            {},
            self.zone_tokens,
            code='missing_but_moving',
        )

    def test_has_tokens_but_absent(self):
        self.teams_data = {
            'ABC': {'zone': 0, 'present': False, 'left_scoring_zone': False},
            'DEF': {'zone': 1, 'present': True, 'left_scoring_zone': False},
        }
        self.assertInvalidScoresheet(
            {'ABC': 'S'},
            self.zone_tokens,
            code='missing_but_has_tokens',
        )


if __name__ == '__main__':
    unittest.main()
