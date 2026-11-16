"""
हर कंपनी का इंटरव्यू स्टाइल। यह आम तौर पर public जानकारी पर आधारित है,
किसी कंपनी की अंदरूनी जानकारी नहीं है। इसे अपने रिसर्च से बढ़ाते रहो:
जितना अच्छा यह लिखा होगा, उतना असली इंटरव्यू लगेगा।
"""

COMPANY_STYLES = {
    "General / HR Round": """
- Warm but professional. Typical questions: tell me about yourself, strengths/weaknesses,
  why this role, why should we hire you, career goals, handling pressure, teamwork.
- Looks for: clear communication, honesty, motivation, cultural fit, realistic expectations.
- Follow up on vague claims with "can you give a specific example?".
""",
    "Amazon": """
- Heavily behavioural, built around the Leadership Principles (Customer Obsession, Ownership,
  Bias for Action, Dive Deep, Earn Trust, Deliver Results, Invent and Simplify, Learn and Be Curious, etc.).
- Expects answers in STAR format (Situation, Task, Action, Result) with concrete metrics.
- Interviewer digs deep with follow-ups: "What exactly did YOU do?", "What was the result in numbers?",
  "What would you do differently?". Penalises "we" answers that hide personal contribution.
- Technical roles also get coding / system design questions.
""",
    "Google": """
- Strong focus on problem solving, analytical thinking and how the candidate reasons aloud.
- Technical roles: data structures and algorithms, complexity analysis, edge cases, clean communication
  while solving; system design for experienced candidates.
- Also checks "Googleyness": collaboration, comfort with ambiguity, intellectual humility, user focus.
- Interviewer gives hints and watches how the candidate responds to them.
""",
    "Microsoft": """
- Mix of technical depth and behavioural questions. Values a growth mindset, collaboration and customer focus.
- Technical roles: coding, design discussions, debugging and trade-offs, explained clearly.
- Behavioural: times you learned from failure, handled conflict, influenced without authority.
- Friendly tone, but follow-ups test how deeply the candidate understands their own work.
""",
    "Indian IT Services (TCS / Infosys / Wipro etc.)": """
- Usually: technical round (core subjects, basic coding, projects), then managerial/HR round.
- Common questions: introduce yourself, explain your final-year project, OOP / DBMS / OS / networking basics,
  strengths and weaknesses, willingness to relocate or work in shifts, where do you see yourself in 5 years.
- Looks for: strong fundamentals, honest project understanding, communication, adaptability.
""",
    "Startup": """
- Informal but sharp. Values ownership, speed, learning ability and breadth over polish.
- Asks about real projects, what you shipped, what broke, how you debugged, how you work with little guidance.
- May ask a practical mini-problem or product-thinking question.
- Looks for: self-starter attitude, curiosity, ability to wear many hats.
""",
}
