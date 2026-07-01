from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

lines = [
    "Jane Doe",
    "jane.doe@example.com | (415) 555-0182",
    "San Francisco, CA",
    "",
    "Summary",
    "Senior backend engineer with 7 years of experience building scalable",
    "distributed systems.",
    "",
    "Skills",
    "Python, Go, Kubernetes, PostgreSQL, AWS, Docker, REST APIs",
    "",
    "Experience",
    "Globex Inc - Senior Backend Engineer (Mar 2021 - Present)",
    "Led the payments platform rewrite.",
    "Initrode - Backend Engineer (Jun 2018 - Feb 2021)",
    "",
    "Education",
    "UC Berkeley - B.S. Computer Science, 2017",
]

path = "data/samples/resume_jane_doe.pdf"

c = canvas.Canvas(path, pagesize=letter)
width, height = letter

y = height - 72
c.setFont("Helvetica", 11)

for line in lines:
    c.drawString(72, y, line)
    y -= 16

c.save()

print("PDF Generated:", path)