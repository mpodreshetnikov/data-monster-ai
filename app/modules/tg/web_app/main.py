from enum import Enum
import logging
import uuid

from mypy_boto3_s3 import S3Client

from .chart_page_app.main import build_chart_page

from modules.brain.main import Answer


logger = logging.getLogger(__name__)


class WebAppTypes(Enum):
    CHART_PAGE = 'chart_page'


class WebApp:
    WEB_APP_PAGES_BUCKET_NAME = "web-app-pages"

    type: WebAppTypes
    base_url: str
    s3client: S3Client

    def __init__(self, web_app_type: WebAppTypes, base_url: str, s3client: S3Client) -> None:
        self.type = web_app_type
        self.base_url = base_url
        self.s3client = s3client
        self.s3client.create_bucket(Bucket=self.WEB_APP_PAGES_BUCKET_NAME)

    def create_and_save(self, answer: Answer) -> str:
        page = self.__build_page__(answer)
        url = self.__save_page__(page)
        logger.log(logging.INFO, f"WebApp page created for (ray_id {answer.ray_id}): {url}")
        return url

    def __build_page__(self, answer: Answer) -> str:
        if self.type == WebAppTypes.CHART_PAGE:
            return build_chart_page(
                answer.chart_data,
                answer.chart_params.label_column,
                answer.chart_params.chart_type.value,
                answer.question
            )
        raise NotImplementedError(
            f"WebApp type {self.type} is not implemented")

    def __save_page__(self, page: str) -> str:
        file_id = str(uuid.uuid4())
        filename = f"{file_id}.html"
        self.s3client.put_object(
            Bucket=self.WEB_APP_PAGES_BUCKET_NAME,
            Key=filename,
            Body=page,
            ContentType="text/html",
            ACL="public-read",
            CacheControl="max-age=3600",
            ContentDisposition="inline",
        )
        url = self.s3client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.WEB_APP_PAGES_BUCKET_NAME,
                "Key": filename,
            },
            ExpiresIn=3600*24*7,
        )
        return url
