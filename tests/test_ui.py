"""Streamlit integration tests: real pages, controls and session preservation."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / 'app.py'
PAGES = ['Dashboard', 'Upload Applicants', 'Job Requirements', 'Candidate Ranking', 'Shortlist Management',
         'Sorting Laboratory', 'Heap Laboratory', 'Hashing Laboratory', 'Performance Analysis', 'Export Reports', 'About Project']


def element(elements, label):
    return next(item for item in elements if item.label == label)


def open_app(page='Dashboard'):
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    if page != 'Dashboard':
        app.sidebar.radio[0].set_value(page).run()
    assert not app.exception
    return app


def test_all_pages_render_without_errors_and_preserve_data():
    app = open_app()
    for page in PAGES:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception, f'{page}: {[error.message for error in app.exception]}'
        assert app.session_state['jr_validation'].summary['valid'] == 72


def test_sorting_lab_runs_and_benchmarks():
    app = open_app('Sorting Laboratory')
    element(app.selectbox, 'Algorithm to run').set_value('Quick Sort')
    element(app.button, 'Run selected sort & verify').click().run()
    assert not app.exception
    assert app.session_state['jr_sort_lab_output']['verified']
    element(app.button, 'Compare all three on this dataset').click().run()
    assert not app.exception
    assert app.session_state['jr_current_sort_benchmark'].verified.all()


def test_heap_lab_k_zero_and_one():
    app = open_app('Heap Laboratory')
    for k in [0, 1]:
        element(app.number_input, 'Candidates to request (K)').set_value(k)
        element(app.button, 'Select top K, compare & verify').click().run()
        assert not app.exception
        assert len(app.session_state['jr_heap_lab_output']['candidates']) == k
        assert app.session_state['jr_heap_lab_output']['verified']


def test_hashing_lookup_miss_and_measurements():
    app = open_app('Hashing Laboratory')
    element(app.text_input, 'Candidate ID to retrieve').set_value('NOT-FOUND')
    element(app.button, 'Look up candidate').click().run()
    assert not app.exception
    assert any('No candidate found' in item.value for item in app.warning)
    element(app.button, 'Measure dictionary vs linear ID lookup').click().run()
    assert not app.exception
    assert app.session_state['jr_current_lookup_benchmark'].verified.all()


def test_invalid_weights_do_not_replace_config():
    app = open_app('Job Requirements')
    original = app.session_state['jr_requirements']
    element(app.number_input, 'Required skills %').set_value(55.0)
    element(app.button, 'Save criteria & recalculate rankings').click().run()
    assert not app.exception
    assert app.session_state['jr_requirements'] == original
    assert any('sum to exactly 100' in item.value for item in app.error)


def test_save_requirements_and_navigation():
    app = open_app('Job Requirements')
    element(app.text_input, 'Job title').set_value('Synthetic Backend Role')
    element(app.checkbox, 'Include education in matching score').uncheck()
    element(app.button, 'Save criteria & recalculate rankings').click().run()
    assert not app.exception
    assert app.session_state['jr_requirements'].title == 'Synthetic Backend Role'
    assert not app.session_state['jr_requirements'].education_rubric
    app.sidebar.radio[0].set_value('Candidate Ranking').run()
    assert not app.exception
    assert app.session_state['jr_requirements'].title == 'Synthetic Backend Role'


def test_manual_override_score_unchanged_on_navigation():
    app = open_app('Shortlist Management')
    score = app.session_state['jr_result'].index.lookup('C072')['final_score']
    element(app.selectbox, 'Candidate to review').set_value('C072').run()
    element(app.selectbox, 'Recruiter review status').set_value('Shortlisted')
    element(app.text_area, 'Review note / reason').set_value('Faculty demonstration: explicit review exception')
    element(app.button, 'Save review decision').click().run()
    assert not app.exception
    assert app.session_state['jr_result'].index.lookup('C072')['is_shortlisted']
    assert app.session_state['jr_result'].index.lookup('C072')['final_score'] == score
    app.sidebar.radio[0].set_value('Dashboard').run()
    app.sidebar.radio[0].set_value('Shortlist Management').run()
    assert not app.exception
    assert app.session_state['jr_result'].index.lookup('C072')['review_note']


def test_manual_decision_requires_note():
    app = open_app('Shortlist Management')
    element(app.selectbox, 'Recruiter review status').set_value('Not shortlisted')
    element(app.button, 'Save review decision').click().run()
    assert not app.exception
    assert any('review note' in item.value for item in app.error)


def test_current_performance_form_executes():
    app = open_app('Performance Analysis')
    element(app.button, 'Measure all current-data algorithms').click().run()
    assert not app.exception
    for key in ['jr_current_sort_benchmark', 'jr_current_heap_benchmark', 'jr_current_lookup_benchmark']:
        assert app.session_state[key].verified.all()
    app.sidebar.radio[0].set_value('Export Reports').run()
    assert not app.exception


def test_generated_benchmark_controls_execute():
    app = open_app('Performance Analysis')
    element(app.multiselect, 'Input sizes (N)').set_value([100])
    element(app.number_input, 'Repetitions per method').set_value(3)
    element(app.button, 'Run measured benchmarks').click().run()
    assert not app.exception
    assert len(app.session_state['jr_generated_sort_benchmark']) == 3
    assert app.session_state['jr_generated_heap_benchmark'].verified.all()
    assert app.session_state['jr_generated_lookup_benchmark'].verified.all()


def test_empty_workspace_all_pages_have_safe_empty_states():
    app = open_app('Upload Applicants')
    element(app.checkbox, 'I understand this clears the current applicant data and review decisions.').check().run()
    element(app.button, 'Clear applicant dataset').click().run()
    assert not app.exception
    assert app.session_state['jr_validation'].summary['uploaded'] == 0
    for page in PAGES:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception, page
    element(app.button, 'Reload synthetic sample').click().run()
    assert not app.exception
    assert app.session_state['jr_validation'].summary['valid'] == 72


def test_reset_manual_decisions_restores_automatic_state():
    app = open_app('Shortlist Management')
    element(app.selectbox, 'Recruiter review status').set_value('Not shortlisted')
    element(app.text_area, 'Review note / reason').set_value('Demonstration exclusion')
    element(app.button, 'Save review decision').click().run()
    assert not app.exception
    assert app.session_state['jr_decisions']
    element(app.checkbox, 'I want to remove every manual status and review note.').check().run()
    element(app.button, 'Return all candidates to Automatic').click().run()
    assert not app.exception
    assert app.session_state['jr_decisions'] == {}
    assert element(app.selectbox, 'Recruiter review status').value == 'Automatic'
    assert element(app.text_area, 'Review note / reason').value == ''


def test_criteria_change_invalidates_current_measurements_and_lab_output():
    app = open_app('Sorting Laboratory')
    element(app.button, 'Run selected sort & verify').click().run()
    element(app.button, 'Compare all three on this dataset').click().run()
    assert 'jr_current_sort_benchmark' in app.session_state
    assert 'jr_sort_lab_output' in app.session_state
    app.sidebar.radio[0].set_value('Job Requirements').run()
    element(app.text_input, 'Job title').set_value('Updated Synthetic Role')
    element(app.button, 'Save criteria & recalculate rankings').click().run()
    assert not app.exception
    assert 'jr_current_sort_benchmark' not in app.session_state
    assert 'jr_sort_lab_output' not in app.session_state
