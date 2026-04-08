import pytest
from unittest.mock import patch, mock_open, MagicMock
import hypercode

# Mock data
MOCK_TOKEN = "test-token-123"
MOCK_FILE_CONTENT = "print('hello world')"
MOCK_API_URL = "http://localhost:8000/api/v1/tasks/"

@pytest.fixture
def mock_token_file():
    with patch("builtins.open", mock_open(read_data=MOCK_TOKEN)) as m:
        yield m

@pytest.fixture
def mock_requests_post():
    with patch("requests.post") as m:
        yield m

def test_get_token_exists(mock_token_file):
    with patch("os.path.exists", return_value=True):
        token = hypercode.get_token()
        assert token == MOCK_TOKEN

def test_get_token_missing():
    with patch("os.path.exists", return_value=False):
        token = hypercode.get_token()
        assert token is None

def test_translate_file_success(mock_requests_post):
    # Mock file existence and content
    with patch("os.path.exists", return_value=True):
        # We need to mock open to handle both token.txt and the source file
        # This is tricky with mock_open, so we'll use a side_effect
        mock_file_map = {
            "token.txt": MOCK_TOKEN,
            "test_file.py": MOCK_FILE_CONTENT
        }
        
        def open_side_effect(filename, *args, **kwargs):
            content = mock_file_map.get(filename)
            if content:
                return mock_open(read_data=content).return_value
            raise FileNotFoundError(filename)

        with patch("builtins.open", side_effect=open_side_effect):
            # Mock successful API response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "task-123"}
            mock_requests_post.return_value = mock_response

            # Capture stdout
            with patch("sys.stdout"):
                hypercode.translate_file("test_file.py")
                
                # Verify API call
                mock_requests_post.assert_called_once()
                args, kwargs = mock_requests_post.call_args
                assert kwargs["json"]["title"] == "CLI Translation: test_file.py"
                assert kwargs["json"]["description"] == MOCK_FILE_CONTENT
                assert kwargs["headers"]["Authorization"] == f"Bearer {MOCK_TOKEN}"

def test_check_pulse_success(mock_requests_post):
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=MOCK_TOKEN)):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "pulse-123"}
            mock_requests_post.return_value = mock_response

            hypercode.check_pulse()
            
            mock_requests_post.assert_called_once()
            args, kwargs = mock_requests_post.call_args
            assert kwargs["json"]["type"] == "health"

def test_research_topic_success(mock_requests_post):
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=MOCK_TOKEN)):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"id": "research-123"}
            mock_requests_post.return_value = mock_response

            hypercode.research_topic("Quantum Computing")
            
            mock_requests_post.assert_called_once()
            args, kwargs = mock_requests_post.call_args
            assert kwargs["json"]["title"] == "Research: Quantum Computing"
            assert kwargs["json"]["type"] == "research"
