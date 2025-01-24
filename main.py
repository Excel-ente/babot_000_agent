import yaml
from rich.console import Console
from rich.prompt import Prompt
from rich.progress import track
from langchain_ollama import OllamaLLM
from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract
import zipfile
import os

# Cargar configuraciones desde un archivo YAML
def cargar_configuracion(config_file="config.yaml"):
    with open(config_file, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)

# Configurar el modelo Ollama
llm = OllamaLLM(model="llama2", base_url="http://localhost:11434")

# Crear una consola rica
console = Console()

class PDFToTextTool:
    def process_zip(self, zip_path: str, output_dir: str, incluir_pdfs: bool) -> str:
        os.makedirs(output_dir, exist_ok=True)
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(output_dir)

            results = []
            for root, _, files in os.walk(output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if file.endswith(".pdf"):
                        text = self.process_pdf(file_path)
                        output_file = os.path.join(output_dir, f"{os.path.splitext(file)[0]}.txt")
                        with open(output_file, "w", encoding="utf-8") as f:
                            f.write(text)
                        results.append(f"Procesado: {output_file}")
                        if not incluir_pdfs:
                            os.remove(file_path)
            return f"Archivos procesados en: {output_dir}\n" + "\n".join(results)
        except Exception as e:
            return f"Error al procesar el ZIP: {e}"

    def process_pdf(self, file_path: str) -> str:
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                extracted_text = page.extract_text()
                if extracted_text:
                    text += extracted_text
                else:
                    text += self.extract_text_with_ocr(file_path)
                    break
            return text
        except Exception as e:
            return f"Error al procesar el PDF: {e}"

    def extract_text_with_ocr(self, file_path: str) -> str:
        try:
            images = convert_from_path(file_path)
            text = ""
            for image in images:
                text += pytesseract.image_to_string(image)
            return text
        except Exception as e:
            return f"Error al realizar OCR: {e}"


class TXTToSummaryTool:
    def run(self, directory: str, prompt: str) -> str:
        try:
            combined_text = ""
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.endswith(".txt"):
                        with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                            combined_text += f.read() + "\n"

            # Generar resumen usando el prompt
            summary = llm.invoke(f"{prompt}\nTexto para resumir:\n{combined_text}")

            # Traducir el resumen al español
            translated_summary = self.translate_to_spanish(summary)

            # Guardar el resumen en un archivo TXT
            output_file = os.path.join(directory, "resumen_final.txt")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(translated_summary)

            return f"Resumen generado y guardado en: {output_file}"
        except Exception as e:
            return f"Error al generar el resumen: {e}"

    def translate_to_spanish(self, text: str) -> str:
        """Traduce el texto proporcionado a español utilizando el modelo de Ollama."""
        try:
            translated_text = llm.invoke(
                f"""
                Traduce el siguiente texto al español sin cambiar el significado:
                {text}
                """
            )
            return translated_text
        except Exception as e:
            return f"Error al traducir el texto: {e}"


def procesar_carpeta_zips(input_dir: str, output_dir: str, incluir_pdfs: bool, prompt: str):
    """Procesa todos los archivos ZIP en una carpeta."""
    for zip_file in os.listdir(input_dir):
        if zip_file.endswith(".zip"):
            zip_path = os.path.join(input_dir, zip_file)
            console.print(f"\n[bold yellow]Procesando archivo ZIP: {zip_file}[/bold yellow]")

            # Crear carpeta específica para este ZIP
            zip_output_dir = os.path.join(output_dir, os.path.splitext(zip_file)[0])
            converter_tool = PDFToTextTool()
            converter_tool.process_zip(zip_path, zip_output_dir, incluir_pdfs)

            # Generar resumen para este ZIP
            summary_tool = TXTToSummaryTool()
            summary_tool.run(zip_output_dir, prompt)


def main():
    console.rule("[bold blue]Analizador de Ordenanzas Fiscales[/bold blue]")

    # Cargar configuraciones
    config = cargar_configuracion()

    ruta_zip = config.get("ruta_zip")
    carpeta_salida = config.get("carpeta_salida")
    incluir_pdfs = config.get("incluir_pdfs", False)
    prompt_resumen = config.get("prompt_resumen")

    # Preguntar si se procesará un solo ZIP o una carpeta con muchos ZIPs
    opcion = Prompt.ask(
        "[bold green]¿Quieres procesar un archivo ZIP único o una carpeta con múltiples ZIPs?[/bold green]",
        choices=["1", "2"],
        default="1",
    )

    if opcion == "1":
        # Procesar un solo archivo ZIP
        console.print("\n[bold yellow]Procesando archivo ZIP único...[/bold yellow]")
        converter_tool = PDFToTextTool()
        result = converter_tool.process_zip(ruta_zip, carpeta_salida, incluir_pdfs)
        console.print("[bold green]Extracción completada.[/bold green]")

        # Generar resumen
        console.print("[bold yellow]Generando resumen...[/bold yellow]")
        summary_tool = TXTToSummaryTool()
        summary_result = summary_tool.run(carpeta_salida, prompt_resumen)
        console.print("\n[bold blue]=== Resultado Final ===[/bold blue]")
        console.print(result)
        console.print(summary_result)

    elif opcion == "2":
        # Procesar todos los ZIPs en una carpeta
        carpeta_zips = Prompt.ask("[bold green]Ingresa la ruta de la carpeta con los ZIPs[/bold green]")
        os.makedirs(carpeta_salida, exist_ok=True)
        procesar_carpeta_zips(carpeta_zips, carpeta_salida, incluir_pdfs, prompt_resumen)
        console.print("[bold blue]=== Procesamiento completado para todos los ZIPs ===[/bold blue]")


if __name__ == "__main__":
    main()
