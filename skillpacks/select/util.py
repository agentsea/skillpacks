def clean_llm_json(input_text: str) -> str:
    cleaned_text = input_text.replace("```", "")

    if cleaned_text.startswith("json\n"):
        cleaned_text = cleaned_text.replace("json\n", "", 1)

    return cleaned_text.strip()
