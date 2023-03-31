import openai, openai.error
import configparser, time, logging

# configure
config = configparser.ConfigParser()
config.read("settings.ini")

openai.api_key = config["openai"]["ApiKey"]
MaxAnswerTokens: int = int(config["openai"]["MaxAnswerTokens"])
ChoicesOneRequest: int = int(config["openai"]["ChoicesOneRequest"])
TestMode: bool = config.getboolean("openai", "TestMode")
RequestTimeoutSeconds: int = int(config["openai"]["RequestTimeoutSeconds"])
LimitRetries: int = int(config["openai"]["LimitRetries"])
RetriesTimeoutSeconds: int = int(config["openai"]["RetriesTimeoutSeconds"])
AiModel: str = config["openai"]["AiModel"]
AiModelType: str = config["openai"]["AiModelType"]
AiEmbeddingModel: str = config["openai"]["EmbeddingModel"]

logger = logging.getLogger(__name__)


class NotCorrectAiAnswerException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class TryAiLaterException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


def generate_answer_code(prompt: str, stop_sequence: list[str] = None) -> list[str]:
    global LimitRetries, RetriesTimeoutSeconds
    return list(map(str.rstrip,
                    __get_ai_responses_with_retries__(
                        lambda _: __get_ai_responses__(prompt, stop_sequence))))


def get_embedding(prompt: str | list[str]) -> list[float] | list[list[float]]:
    global RequestTimeoutSeconds, AiModel
    response = openai.Embedding.create(
        model=AiEmbeddingModel,
        input=prompt,
    )
    data = response.data
    if len(data) == 1:
        return data[0].embedding
    else:
        return list(map(lambda x: x.embedding, data))


def __list_ai_models__() -> list[str]:
    models = openai.Model.list()
    models_names = list(map(lambda x: x.openai_id, models.data))
    return models_names
logger.info(__list_ai_models__())


def __get_ai_responses__(prompt: str, stop_sequence: list[str] = None) -> list[str]:
    global ChoicesOneRequest, TestMode, RequestTimeoutSeconds, AiModel, AiModelType, MaxAnswerTokens

    if TestMode:
        logger.info("Returned Test Mode default answer")
        return ["* FROM pg_catalog.pg_namespace"]

    if stop_sequence is None: stop_sequence = ["#", ";"]

    logger.info("Asking AI...")
    
    temperature = 0.05

    if AiModelType == "completion":
        response = openai.Completion.create(
            model=AiModel,
            prompt=prompt,
            temperature=temperature,
            max_tokens=MaxAnswerTokens,
            stop=stop_sequence,
            n=ChoicesOneRequest,
            request_timeout=RequestTimeoutSeconds,
        )
    elif AiModelType == "chat":
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                    {"role": "system", "content": "You are a helpful assystant for code and data analysis. You help to write SQL and Python code. You can also show data in tables and plots."},
                    {"role": "user", "content": prompt}
                ],
            temperature=temperature,
            max_tokens=MaxAnswerTokens,
            n=ChoicesOneRequest,
            request_timeout=RequestTimeoutSeconds,
        )
    if not response: raise Exception("AI model type is not supported")

    str_ai_answers_reasons = ', '.join(map(lambda x: f'[{x.finish_reason}]', response.choices))
    logger.info(f"AI {response.model}/{response.response_ms}ms. Tokens: {response.usage.prompt_tokens}prompt, {response.usage.completion_tokens}completion. Answers-metadata: {str_ai_answers_reasons}")

    possible_answers = filter(lambda x: x.finish_reason == "stop", response.choices)
    if AiModelType == "completion":
        logger.info(list(map(lambda x: x.text, response.choices)))
        answers_text = list(map(lambda x: x.text, possible_answers))
    elif AiModelType == "chat":
        logger.info(list(map(lambda x: x.message.content, response.choices)))
        answers_text = list(map(lambda x: x.message.content, possible_answers))

    logger.info(f"There are {len(answers_text)} correct answers")

    if len(answers_text) == 0:
        raise NotCorrectAiAnswerException("AI answer was long or infinite. Try to increase 'max_tokens' or change the prompt.")
    return answers_text


def __get_ai_responses_with_retries__(
        call: callable,
        retries_limit: int = None,
        retries_timeout_seconds: int = None
        ) -> any:
    retries_limit = retries_limit or LimitRetries
    retries_timeout_seconds = retries_timeout_seconds or RetriesTimeoutSeconds
    
    logger.info(f"Asking AI with {retries_limit} retries and {retries_timeout_seconds}s timeout")
    for retry in range(retries_limit):
        try:
            if retry != 0:
                logger.info('Waiting timeout...')
                time.sleep(retries_timeout_seconds)
            logger.info(f'Trying {retry + 1}...')
            return call()
        except (
            openai.error.RateLimitError,
            openai.error.Timeout,
            openai.error.TryAgain,
            openai.error.ServiceUnavailableError,
            openai.error.APIError,
            NotCorrectAiAnswerException
        ) as e:
            logger.info(str(e))
            continue
        except openai.error.APIConnectionError as e:
            if e.should_retry:
                logger.info(str(e))
                continue
            else: raise e
    raise TryAiLaterException(f"Cannot get an answer: {retries_limit} retries with {retries_timeout_seconds}s sleep between. Try again later.")