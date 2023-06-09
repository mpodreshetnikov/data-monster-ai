import datetime
import csv
import logging


logger = logging.getLogger(__name__)

# comment: StatisticWriter is not used anywhere, let's remove it.
class StatisticWriter:
    @staticmethod
    def add_statistic(statistic: str, chat_id: str, message_id: str, username: str, user_id: str, question: str):
        try:
            if statistic:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(statistic, "a", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    if f.tell() == 0:  # Check if the file is empty
                        writer.writerow(["unique_message_id", "Timestamp", "User", "Question", "Successful", "SQL", "Answer", "Error"])
                    writer.writerow([
                        f"{chat_id}_{message_id}",
                        timestamp,
                        f"{username}:{user_id}",
                        question,
                        None,
                        None,
                        None,
                        None,
                    ])
        except Exception as e:
            logger.error("StatisticWriter. An unexpected error occurred", str(e), exc_info=True)

    @staticmethod
    def update_field(statistic: str, chat_id: str, message_id: str, field_name: str, field_value):
        try:
            if statistic:
                unique_message_id = f"{chat_id}_{message_id}"
                with open(statistic, "r+", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    header = rows[0]  # Get the header row
                    unique_message_id_index = header.index("unique_message_id")
                    field_index = header.index(field_name)
                    for row in rows[1:]:  # Skip header row
                        if row and row[unique_message_id_index] == unique_message_id:
                            if len(row) < len(header):  # Fill empty values if row length is less than header length
                                row.extend([''] * (len(header) - len(row)))
                            row[field_index] = field_value
                            break
                    f.seek(0)  # Move the file pointer to the beginning
                    writer = csv.writer(f)
                    writer.writerows(rows)
                    f.truncate()
        except Exception as e:
            logger.error(f"Failed to update {field_name} field in CSV file:", str(e), exc_info=True)

    @staticmethod
    def true_successful(statistic: str, chat_id: str, message_id: str, sql_script: str, answer:str):
        StatisticWriter.update_field(statistic, chat_id, message_id, "Successful", "True")
        StatisticWriter.update_field(statistic, chat_id, message_id, "SQL", sql_script)
        StatisticWriter.update_field(statistic, chat_id, message_id, "Answer", answer)

    @staticmethod
    def false_successful(statistic: str, chat_id: str, message_id: str, error: str):
        StatisticWriter.update_field(statistic, chat_id, message_id, "Successful", "False")
        StatisticWriter.update_field(statistic, chat_id, message_id, "Error", error)
