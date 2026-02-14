import re


def parse_questions_answers(file_path="questions/9krug17.txt"):
    with open(file_path, "r", encoding="koi8-r") as file:
        content = file.read()

    blocks = content.split("\n\n")

    questions_answers = {}
    current_question = None

    for block in blocks:
        block = block.strip()

        if block.startswith("Вопрос"):

            question = block.split(":", 1)[1].strip()
            question = question.replace("\n", " ")
            current_question = question

        elif block.startswith("Ответ:") and current_question:
            answer = block.replace("Ответ:", "").strip()
            answer = answer.replace("\n", " ")
            questions_answers[current_question] = answer
            current_question = None

    return questions_answers


def clean_answer(answer):

    answer = re.sub(r"\(.*?\)", "", answer)

    answer = answer.split(".")[0]

    return answer.strip().lower()
