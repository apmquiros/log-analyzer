from flask import Flask, render_template, request, Response, make_response
import re
import csv
import io

app = Flask(__name__)

last_logs = None

@app.route("/", methods=["GET", "POST"])
def index():
    global last_logs
    logs = None

    if request.method == "POST":
        file = request.files["logfile"]
        ip = request.form.get("search_ip")
        keyword = request.form.get("search_keyword")
        custom_regex = request.form.get("search_regex")

        if file:
            content = file.read().decode("utf-8")
            logs = parse_logs(content, ip, keyword, custom_regex)
            last_logs = logs

    return render_template("index.html", logs=logs)

def parse_logs(content, ip=None, keyword=None, custom_regex=None):
    lines = content.splitlines()
    matches = []
    errors, warns, infos, failed = [], [], [], []

    filters_applied = any([ip, keyword, custom_regex])

    for line in lines:
        line_category = "Raw"  
        if re.search(r"ERROR", line):
            errors.append(line)
            line_category = "ERROR"
        elif re.search(r"WARN", line):
            warns.append(line)
            line_category = "WARN"
        elif re.search(r"INFO", line):
            infos.append(line)
            line_category = "INFO"
        elif re.search(r"Failed", line, re.IGNORECASE):
            failed.append(line)
            line_category = "FAILED"

        if filters_applied:
            if ip and ip in line:
                matches.append({ "level": "Custom", "line": line })
            elif keyword and keyword.lower() in line.lower():
                matches.append({ "level": "Custom", "line": line })
            elif custom_regex and re.search(custom_regex, line):
                matches.append({ "level": "Custom", "line": line })
        else:
            matches.append({ "level": line_category, "line": line })

    return {
        "matches": matches,
        "errors": errors,
        "warns": warns,
        "infos": infos,
        "failed": failed,
        "total_lines": len(lines)
    }

@app.route("/download/csv")
def download_csv():
    global last_logs
    if not last_logs:
        return "No log data available to download."

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Level', 'Log Line'])

    for item in last_logs['matches']:
        writer.writerow([item['level'], item['line']])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=log_matches.csv"}
    )

@app.route("/download/txt")
def download_txt():
    global last_logs
    if not last_logs:
        return "No log data available to download."

    output = io.StringIO()
    for item in last_logs['matches']:
        output.write(f"[{item['level']}] {item['line']}\n")

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=log_matches.txt'
    response.mimetype = 'text/plain'
    return response

if __name__ == "__main__":
    app.run(debug=True)
