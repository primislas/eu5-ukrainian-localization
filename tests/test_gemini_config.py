from ukrainersalis_utils.gemini_translator import GeminiTranslator
from google.genai.types import HttpOptions, HttpRetryOptions

def test_gemini_client_retry_config(mocker):
    # Mock the genai.Client class
    mock_client_class = mocker.patch("google.genai.Client")
    mock_client_instance = mock_client_class.return_value
    
    # Mock the generate_content method to return a dummy response
    mock_response = mocker.Mock()
    mock_response.text = "Translated text"
    mock_client_instance.models.generate_content.return_value = mock_response

    translator = GeminiTranslator()
    
    # Trigger the client initialization and translation
    result = translator.translate("Some source text")
    
    # 1. Verify client was initialized with correct retry config
    mock_client_class.assert_called_once()
    _, kwargs = mock_client_class.call_args
    assert "http_options" in kwargs
    http_options = kwargs["http_options"]
    assert isinstance(http_options, HttpOptions)
    assert http_options.retry_options is not None
    assert isinstance(http_options.retry_options, HttpRetryOptions)
    assert http_options.retry_options.attempts == 5

    # 2. Verify translate actually called generate_content with the correct parameters
    mock_client_instance.models.generate_content.assert_called()
    assert result == "Translated text"
