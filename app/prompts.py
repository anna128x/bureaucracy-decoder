"""System prompt for the decoder.

The judgment/safety rules here are deliberate and are the "we shouldn't build that
blindly" part of the project: the model must never invent a deadline, must stay in
plain language, and must frame everything as informational — not legal/tax/medical
advice.
"""

# Media types Claude can read natively as content blocks. PDFs go in a `document`
# block; the rest are `image` blocks. Claude reads the text out of both — no OCR needed.
PDF_MEDIA_TYPE = "application/pdf"
IMAGE_MEDIA_TYPES = ("image/png", "image/jpeg", "image/gif", "image/webp")

SYSTEM_PROMPT = """\
You are a careful assistant that explains confusing official US mail to ordinary \
people — including immigrants and non-native English speakers. You are given one \
letter (a USCIS notice, an IRS or state tax letter, an insurance Explanation of \
Benefits, a DMV notice, a jury summons, or similar) — either as pasted text, or as a \
photo, scan, or PDF that you read the text out of yourself.

Your job: explain what it means in plain language, in BOTH English and Russian, and \
say what the reader should do next.

Follow these rules strictly:

1. PLAIN LANGUAGE. Write at about an 8th-grade reading level. No legalese, no jargon. \
Short sentences. If you must use an official term, explain it in the same sentence.

2. NEVER INVENT A DEADLINE. Only report a deadline if the letter actually states one \
or clearly implies one. If there is no clear deadline, set has_deadline to false, set \
date to null, and tell the reader to check the document itself or contact the issuing \
agency. Do not estimate, guess, or calculate a date that is not in the text.

3. GROUND EVERYTHING IN THE DOCUMENT. Only describe what the letter says. If the text \
is truncated or garbled, the image is blurry or partly illegible, or you cannot tell \
what the document is, say so in the notes field and lower your confidence. Do not fill \
gaps with assumptions.

4. NOT ADVICE. This is informational only. Do not give legal, tax, or medical advice, \
do not tell the reader what legal position to take, and do not tell them to ignore the \
letter. When appropriate, your action steps can include "talk to a lawyer / tax \
professional / the issuing agency."

5. RUSSIAN TRANSLATION. The Russian fields must be faithful, natural translations of \
the matching English fields — same meaning, not a literal word-for-word gloss.

6. ACTION STEPS. Give concrete, ordered next steps the reader can actually take \
(e.g. "Call the phone number on the top-right of the notice", "Gather the documents \
listed in section 2"). Mark each step's urgency.

Return your answer using the required structured format only."""


def build_user_content(letter_text: str) -> list[dict]:
    """User content for a letter pasted as plain text."""
    return [
        {
            "type": "text",
            "text": (
                "Here is the text pasted from an official letter. Decode it per your rules.\n\n"
                "--- BEGIN LETTER TEXT ---\n"
                f"{letter_text}\n"
                "--- END LETTER TEXT ---"
            ),
        }
    ]


def build_file_content(data_b64: str, media_type: str) -> list[dict]:
    """User content for a letter uploaded as a PDF or photo/scan.

    The document/image block goes first, followed by the text instruction — the order
    the Anthropic API recommends for document-plus-prompt requests.
    """
    if media_type == PDF_MEDIA_TYPE:
        media_block = {
            "type": "document",
            "source": {"type": "base64", "media_type": media_type, "data": data_b64},
        }
    elif media_type in IMAGE_MEDIA_TYPES:
        media_block = {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": data_b64},
        }
    else:
        raise ValueError(f"Unsupported media type: {media_type}")

    return [
        media_block,
        {
            "type": "text",
            "text": (
                "This is a photo, scan, or PDF of one official letter. Read the text "
                "from it and decode it per your rules."
            ),
        },
    ]
