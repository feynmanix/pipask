from pipc.main import hello_world

def test_hello_world():
    result = hello_world()
    assert result == "Hello, World!"
