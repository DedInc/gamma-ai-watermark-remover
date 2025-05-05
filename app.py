import os
from quart import Quart, request, send_file, render_template, Response
from werkzeug.utils import secure_filename
from watermark_detector import WatermarkDetector
from watermark_remover import WatermarkRemover

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}

app = Quart(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

detector = WatermarkDetector()
remover = WatermarkRemover()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET'])
async def index():
    return await render_template('index.html')

@app.route('/remove_watermark', methods=['POST'])
async def remove_watermark():
    error_message = None
    success_message = None
    output_file_path = None
    output_filename = None

    files = await request.files
    if 'pdf_file' not in files:
        error_message = 'No file part. Please upload a PDF.'
        return await render_template('index.html', error_message=error_message)

    file = files['pdf_file']
    if file.filename == '':
        error_message = 'No selected file. Please choose a PDF file.'
        return await render_template('index.html', error_message=error_message)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            await file.save(upload_path)

            images_to_remove_info, error = detector.identify_watermarks(upload_path)
            if error:
                raise Exception(error)

            if images_to_remove_info:
                output_filename = 'processed_' + filename
                output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
                processed_pdf_path, error = remover.remove_watermarks(upload_path, images_to_remove_info, output_path)
                if error:
                    raise Exception(error)
                output_file_path = processed_pdf_path
                success_message = 'Watermarks removed successfully!'
            else:
                success_message = 'No watermarks found in the PDF.'
                output_file_path = upload_path

        except Exception as e:
            error_message = f'Error processing file: {str(e)}'
            if os.path.exists(upload_path):
                os.remove(upload_path)
            return await render_template('index.html', error_message=error_message)

        finally:
            if os.path.exists(upload_path) and success_message is not None and output_file_path != upload_path:
                 os.remove(upload_path)

        if success_message:
            if output_file_path and output_filename:
                response = await send_file(output_file_path, as_attachment=True)
                response.headers["Content-Disposition"] = f"attachment; filename={output_filename}"
                return response
            else:
                return await render_template('index.html', success_message=success_message)
        else:
            return await render_template('index.html', error_message=error_message if error_message else "Unknown error")

    else:
        error_message = 'Invalid file type. Please upload a PDF file.'
        return await render_template('index.html', error_message=error_message)

if __name__ == '__main__':
    app.run(debug=True)