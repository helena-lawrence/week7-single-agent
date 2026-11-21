from memory_tools import create_memory_tools


def test_user_isolation():
    t_a = create_memory_tools('test-A')
    t_b = create_memory_tools('test-B')
    assert 'saved' in t_a[0].invoke({'category': 'explanation', 'value': 'Use small examples'}).lower()
    assert 'Use small examples' in t_a[1].invoke({})
    assert 'Use small examples' not in t_b[1].invoke({})


def test_secret_rejected():
    saver = create_memory_tools('test-A')[0]
    assert 'Rejected' in saver.invoke({'category': 'secret', 'value': 'password 1234'})
