import base64

def encode_file_base64(file):
    file_content = file.read()
    base64_string = base64.b64encode(file_content).decode("utf-8")
    return base64_string