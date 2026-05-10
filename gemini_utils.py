from google import genai
from google.genai import types
import os
import io
import base64
import json
import time
import PIL.Image

# Urutan model fallback jika quota habis
MODELS_FALLBACK = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.5-flash",
]


def _get_client():
    """Buat Gemini client dengan API key dari env"""
    api_key = os.getenv("GEMINI_API_KEY")
    return genai.Client(api_key=api_key)


def _call_with_fallback(build_fn, max_retries: int = 2):
    """
    Coba panggil Gemini dengan retry dan fallback model.
    build_fn(client, model_name) -> response
    """
    client = _get_client()
    last_error = None

    for model_name in MODELS_FALLBACK:
        for attempt in range(max_retries):
            try:
                return build_fn(client, model_name)
            except Exception as e:
                err_str = str(e)
                if (
                    "429" in err_str
                    or "quota" in err_str.lower()
                    or "RESOURCE_EXHAUSTED" in err_str
                ):
                    if attempt < max_retries - 1:
                        time.sleep(5)
                        continue
                    last_error = e
                    break
                else:
                    raise e

    raise last_error


def get_gemini_response(messages: list, system_prompt: str = None) -> str:
    try:
        if system_prompt is None:
            system_prompt = """You are a smart AI assistant for personal finance management.
Your tasks:
1. Help users analyze their spending and transactions
2. Provide insights about their spending patterns
3. Answer questions about their budget and finances
4. Give practical recommendations to save money

IMPORTANT: Always reply in the SAME language the user is using.
If the user writes in English, reply in English.
If the user writes in Indonesian (Bahasa Indonesia), reply in Indonesian.
If the user writes in another language, match that language.

Use a friendly and professional tone.
Base your answers on the transaction data provided.
Do not give specific investment advice — focus on saving and budgeting tips."""

        # Konversi format messages ke format SDK baru
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(
                types.Content(role=role, parts=[types.Part(text=msg["content"])])
            )

        def build_fn(client, model_name):
            return client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7,
                    max_output_tokens=1024,
                ),
            )

        response = _call_with_fallback(build_fn)
        return response.text

    except Exception as e:
        err = str(e)
        if "429" in err or "quota" in err.lower() or "RESOURCE_EXHAUSTED" in err:
            return "⚠️ Quota API Gemini habis untuk saat ini. Coba lagi beberapa menit kemudian."
        return f"Error: {err}"


def extract_receipt_data(image_base64: str, mime_type: str = "image/jpeg"):
    """
    Baca struk belanja dari gambar menggunakan Gemini Vision.
    Return dict {merchant, description, amount, category} atau None jika gagal.
    """
    try:
        prompt = """Kamu adalah AI yang ahli membaca struk belanja Indonesia.
Baca struk ini dan ekstrak informasi berikut dalam format JSON:

{
  "merchant": "nama toko/merchant",
  "description": "deskripsi singkat pembelian (maks 50 karakter)",
  "amount": total_belanja_sebagai_angka_saja,
  "category": "salah satu dari: Food, Transport, Entertainment, Utility/Bills, Shopping, Other"
}

Aturan:
- "amount" harus angka murni tanpa Rp, titik, atau koma (contoh: 75000)
- Jika ada beberapa item, gunakan total akhir sebagai amount
- Jika nama merchant tidak jelas, tebak dari konteks struk
- Pilih category yang paling sesuai dari daftar di atas
- Hanya balas dengan JSON saja, tanpa teks lain"""

        img_bytes = base64.b64decode(image_base64)
        image = PIL.Image.open(io.BytesIO(img_bytes))

        # Konversi PIL Image ke bytes untuk SDK baru
        buf = io.BytesIO()
        fmt = "JPEG" if "jpeg" in mime_type or "jpg" in mime_type else "PNG"
        image.save(buf, format=fmt)
        img_data = buf.getvalue()

        def build_fn(client, model_name):
            return client.models.generate_content(
                model=model_name,
                contents=[
                    types.Content(
                        parts=[
                            types.Part(text=prompt),
                            types.Part(
                                inline_data=types.Blob(
                                    mime_type=mime_type,
                                    data=img_data,
                                )
                            ),
                        ]
                    ),
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=512,
                ),
            )

        response = _call_with_fallback(build_fn)

        raw = response.text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)

        if "merchant" in data and "amount" in data:
            amount_str = str(data["amount"])
            if amount_str.count(".") > 1:
                amount_str = amount_str.replace(".", "")
            amount_str = amount_str.replace(",", "")
            data["amount"] = float(amount_str)
            return data

        return None

    except Exception as e:
        print(f"extract_receipt_data error: {e}")
        err = str(e)
        if "429" in err or "quota" in err.lower() or "RESOURCE_EXHAUSTED" in err:
            raise Exception("quota_exceeded")
        return None


def analyze_spending(transactions_text: str) -> str:
    messages = [
        {
            "role": "user",
            "content": f"""Analisis pengeluaran saya berikut dan berikan insights:

{transactions_text}

Tolong berikan:
1. Kategori dengan pengeluaran tertinggi
2. Pola spending (harian, mingguan, bulanan)
3. 3 rekomendasi untuk menghemat uang
4. Perbandingan dengan rata-rata Indonesia (jika memungkinkan)""",
        }
    ]
    return get_gemini_response(messages)


def categorize_transaction(merchant: str, description: str, amount: float) -> str:
    messages = [
        {
            "role": "user",
            "content": f"""Kategorikan transaksi berikut ke salah satu kategori ini:
Food, Transport, Entertainment, Utility/Bills, Shopping, Other

Merchant: {merchant}
Deskripsi: {description}
Jumlah: Rp {amount:,.0f}

Hanya jawab dengan nama kategori saja.""",
        }
    ]
    response = get_gemini_response(messages)
    for cat in [
        "Food",
        "Transport",
        "Entertainment",
        "Utility/Bills",
        "Shopping",
        "Other",
    ]:
        if cat.lower() in response.lower():
            return cat
    return "Other"


def generate_budget_recommendation(spending_data: str, budget_data: str) -> str:
    messages = [
        {
            "role": "user",
            "content": f"""Berdasarkan data pengeluaran dan budget saya:

PENGELUARAN AKTUAL:
{spending_data}

BUDGET YANG DI-SET:
{budget_data}

Berikan rekomendasi:
1. Kategori mana yang over budget?
2. Seberapa signifikan overnya?
3. Saran penyesuaian budget untuk bulan depan
4. Tips menghemat untuk kategori yang over budget""",
        }
    ]
    return get_gemini_response(messages)


def chat_with_gemini(user_message: str, chat_history: list) -> tuple[str, list]:
    chat_history.append({"role": "user", "content": user_message})
    response = get_gemini_response(chat_history)
    chat_history.append({"role": "assistant", "content": response})
    return response, chat_history


# Alias compatibility
get_claude_response = get_gemini_response
chat_with_claude = chat_with_gemini
