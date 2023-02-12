from sr.comp.scorer import Converter as BaseConverter


class Converter(BaseConverter):
    def form_team_to_score(self, form, zone_id):
        left_scoring_zone = form.get(f'left_scoring_zone_{zone_id}')
        robot_tokens = form.get(f'robot_tokens_{zone_id}') or ''
        return {
            **super().form_team_to_score(form, zone_id),
            'left_scoring_zone': left_scoring_zone is not None,
            'robot_tokens': robot_tokens,
        }

    def score_to_form(self, score):
        form = super().score_to_form(score)

        for info in score['teams'].values():
            zone_id = info['zone']
            form[f'left_scoring_zone_{zone_id}'] = info.get(
                'left_scoring_zone',
                False,
            )
            form[f'robot_tokens_{zone_id}'] = info.get('robot_tokens', '')

        return form

    def match_to_form(self, match):
        form = super().match_to_form(match)

        for zone_id, tla in enumerate(match.teams):
            if tla:
                form[f'left_scoring_zone_{zone_id}'] = False
                form[f'robot_tokens_{zone_id}'] = ''

        return form
