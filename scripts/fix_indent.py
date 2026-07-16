"""Fix indentation: de-indent the status display block from 16 to 12 spaces."""
content = open("app.py", encoding="utf-8").read()

# Find the over-indented block start
start_marker = "            app_id_display = rec.get"
end_marker   = "# PAGE: Case Queue"

start_idx = content.index(start_marker)
# Skip past the app_id_display line itself
start_idx = content.index("\n", start_idx) + 1
end_idx   = content.index(end_marker)

block = content[start_idx:end_idx]

# Lines starting with 16 spaces need to be reduced to 12
fixed_lines = []
for line in block.splitlines(keepends=True):
    if line.startswith("                "):  # 16 spaces
        fixed_lines.append("            " + line[16:])
    else:
        fixed_lines.append(line)

fixed_block = "".join(fixed_lines)
new_content = content[:start_idx] + fixed_block + content[end_idx:]
open("app.py", "w", encoding="utf-8").write(new_content)
print("Done, lines fixed:", sum(1 for l in block.splitlines() if l.startswith("                ")))
