import openai, openai.error
import configparser, time, logging

# configure
config = configparser.ConfigParser()
config.read("settings.ini")

openai.api_key = config["openai"]["ApiKey"]
ChoicesOneRequest: int = int(config["openai"]["ChoicesOneRequest"])
TestMode: bool = config.getboolean("openai", "TestMode")
LimitRetries: int = int(config["openai"]["LimitRetries"])
RetriesTimeoutSeconds: int = int(config["openai"]["RetriesTimeoutSeconds"])


logger = logging.getLogger(__name__)


class NotCorrectAiAnswerException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class TryAiLaterException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


def get_ai_responses(prompt: str) -> list[str]:
    global ChoicesOneRequest, TestMode

    if TestMode:
        logger.info("Returned Test Mode default answer")
        return ["* from"]

    logger.info("Asking AI...")
    response = openai.Completion.create(
        model="code-davinci-002",
        prompt=prompt,
        temperature=0.05,
        max_tokens=1000,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        stop=["#", ";"],
        n=ChoicesOneRequest,
    )

    str_ai_answers = ', '.join(map(lambda x: f'[{x.finish_reason}]', response.choices))
    logger.info(f"AI {response.model}/{response.response_ms}ms. Tokens: {response.usage.prompt_tokens}prompt, {response.usage.completion_tokens}completion. Answers-metadata: {str_ai_answers}")
    logger.info(list(map(lambda x: x.text, response.choices)))

    possible_answers = list(map(lambda x: x.text, filter(lambda x: x.finish_reason == "stop", response.choices)))
    logger.info(f"There are {len(possible_answers)} correct answers")

    if len(possible_answers) == 0:
        raise NotCorrectAiAnswerException("AI answer was long or infinite. Try to increase 'max_tokens' or change the prompt.")
    return possible_answers


def get_ai_responses_with_retries(prompt: str, retries_limit: int, retries_timeout_seconds: int) -> list[str]:
    logger.info(f"Asking AI with {retries_limit} retries and {retries_timeout_seconds}s timeout")
    for retry in range(retries_limit):
        try:
            if retry != 0:
                logger.info('Waiting timeout...')
                time.sleep(retries_timeout_seconds)
            logger.info(f'Trying {retry + 1}...')
            return get_ai_responses(prompt)
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


def generate_answer_code(prompt: str) -> list[str]:
    global LimitRetries, RetriesTimeoutSeconds
    ai_responses = get_ai_responses_with_retries(prompt, LimitRetries, RetriesTimeoutSeconds)
    return list(map(lambda x: f"SELECT {x}", ai_responses))