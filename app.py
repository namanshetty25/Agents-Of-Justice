import streamlit as st
from crewai import Agent, Task, Crew, Process, LLM

# Load environment variables
import os
import streamlit as st

# Use Streamlit secrets 
if "GROQ_API_KEY" not in st.secrets:
    st.error("GROQ_API_KEY not found. Please set it in Streamlit secrets.")
    st.stop()

os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

# Page config
st.set_page_config(page_title="Agent of Justice", layout="wide")
st.title("Agent of Justice - Supreme Court Simulation")

# Sidebar with example cases
with st.sidebar:
    st.header("Example Supreme Court Cases")
    example_cases = {
        "Select an example...": "",
        "Punjab Water Board v. Contractor (Arbitration Deposit Clause)": """
        In 2008, Punjab State Water Supply Board issued tender for water supply and sewerage works on turnkey basis.
        Appellant company was awarded the contract in 2008, formal agreement signed in 2009.
        Clause 25(viii) of the tender required any party invoking arbitration to deposit 10% of the claimed amount
        as a call deposit in the name of the arbitrator. On award, only proportional amount refunded if claimant succeeds;
        balance forfeited to the other party even if the other party loses the case.
        Contractor challenged this clause as arbitrary, violative of Article 14, and a clog on arbitration.
        High Court dismissed challenge. Appeal to Supreme Court.
        """,
        "Andhra Pradesh Promotions Case (Prospective Overruling)": """
        Dispute over G.O.Ms allowing Senior Assistants/Stenographers from Head Office and other departments
        to be considered for promotion by transfer to Assistant Labour Officer posts in Labour Department,
        allegedly violating Presidential Order under Article 371-D (zonal/local cadre system).
        State Administrative Tribunal struck down the G.O.Ms but saved past promotions (prospective effect).
        High Court overturned the saving of past promotions, making declaration retrospective.
        Affected promoted employees challenged, arguing doctrine of prospective overruling should apply.
        """,
        "Chanmuniya v. Virendra Kumar (Live-in Relationships & Maintenance)": """
        Woman claimed she was married to the man in 1986 per Hindu rites, lived together 2-3 years,
        then he deserted her. Filed maintenance under Section 125 CrPC in 2001.
        Man claimed he was already married to another woman (Lakshmi) since 1980 with a son.
        Family Court and High Court held the claimant was the wife.
        Issue: Can a woman in a 'relationship in the nature of marriage' (live-in) claim maintenance
        under Domestic Violence Act 2005 even if not legally wedded wife? Meaning of 'relationship in the nature of marriage'.
        Also, effect of not impleading the first wife.
        """
    }

    selected_example = st.selectbox("Load example case", list(example_cases.keys()))
    if selected_example != "Select an example...":
        case_text = example_cases[selected_example]
    else:
        case_text = st.session_state.get("case_text", "")

    st.markdown("### Instructions")
    st.info("Paste or select a case summary. The AI will simulate a Supreme Court hearing with arguments, jury deliberation, and verdict.")

# Main case input
case_text = st.text_area(
    "Case Summary",
    value=case_text,
    height=220,
    placeholder="Paste full judgment or case summary here..."
)

col1, col2 = st.columns([1, 1])
with col1:
    start_trial = st.button("Start Simulation", type="primary", use_container_width=True)
with col2:
    clear = st.button("Clear", use_container_width=True)

if clear:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

st.session_state.case_text = case_text

if start_trial:
    if not case_text.strip():
        st.warning("Please provide or select a case summary.")
        st.stop()

    tab_args, tab_delib, tab_verdict = st.tabs([
        "Opening Arguments",
        "Jury Deliberation",
        "Final Verdict"
    ])

    # LLMs
    llm_logic = LLM(model="groq/llama-3.3-70b-versatile", temperature=0.15, max_completion_tokens=2048)
    llm_jury = LLM(model="groq/llama-3.1-8b-instant", temperature=0.8, max_completion_tokens=1024)

    # Agents
    judge = Agent(role="Presiding Judge", goal="Moderate proceedings and deliver reasoned judgment.", backstory="Senior Supreme Court judge.", llm=llm_logic, verbose=True)
    petitioner = Agent(role="Petitioner Counsel", goal="Argue for the appeal.", backstory="Advocate for the affected employees.", llm=llm_logic, verbose=True)
    respondent = Agent(role="Respondent Counsel", goal="Defend the High Court decision.", backstory="Advocate for the State.", llm=llm_logic, verbose=True)
    juror_1 = Agent(role="Juror #1 (Analytical)", goal="Evaluate logic and precedent.", backstory="Former law professor.", llm=llm_jury, verbose=True)
    juror_2 = Agent(role="Juror #2 (Equitable)", goal="Consider fairness and impact.", backstory="Social justice advocate.", llm=llm_jury, verbose=True)
    juror_3 = Agent(role="Juror #3 (Skeptical)", goal="Challenge assumptions.", backstory="Retired High Court judge.", llm=llm_jury, verbose=True)

    # Clean display helper (no emojis, proper titles only)
    def display_chat(transcript, container):
        lines = transcript.split("\n")
        current_speaker = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if ":" in line and any(keyword in line for keyword in ["Judge", "Counsel", "Petitioner", "Respondent", "Juror"]):
                speaker, text = line.split(":", 1)
                speaker = speaker.strip()
                text = text.strip()

                if "Judge" in speaker:
                    display_name = "Presiding Judge"
                elif "Petitioner" in speaker or "Appellant" in speaker:
                    display_name = "Petitioner Counsel"
                elif "Respondent" in speaker or "Defense" in speaker:
                    display_name = "Respondent Counsel"
                elif "Juror" in speaker:
                    display_name = speaker.strip()
                else:
                    display_name = speaker

                container.markdown(f"**{display_name}**")
                container.markdown(text)
                current_speaker = display_name
            elif current_speaker:
                container.markdown(line)

    # Phase 1: Arguments
    with tab_args:
        with st.spinner("Hearing arguments..."):
            task_args = Task(
                description=f"""
                Simulate Supreme Court oral arguments based ONLY on this case:
                {case_text}
                Petitioner Counsel opens, Respondent Counsel responds, Presiding Judge moderates.
                Use exact speaker titles: Presiding Judge, Petitioner Counsel, Respondent Counsel.
                Produce a clean transcript with no emojis, no extra symbols, no stage directions.
                """,
                expected_output="Transcript of arguments.",
                agent=judge
            )
            crew_args = Crew(agents=[judge, petitioner, respondent], tasks=[task_args], process=Process.sequential, verbose=False)
            result_args = crew_args.kickoff()
            args_text = result_args.raw
            display_chat(args_text, tab_args)

    # Phase 2: Deliberation
    with tab_delib:
        with st.spinner("Jury deliberating..."):
            task_delib = Task(
                description=f"""
                Three jurors deliberate on these arguments:
                {args_text}
                Each juror speaks using their full role name: Juror #1 (Analytical), etc.
                End with clear vote count and majority reasoning.
                No emojis, no extra symbols, no stage directions.
                """,
                expected_output="Deliberation transcript.",
                agent=juror_1
            )
            crew_delib = Crew(agents=[juror_1, juror_2, juror_3], tasks=[task_delib], process=Process.sequential, verbose=False)
            result_delib = crew_delib.kickoff()
            delib_text = result_delib.raw
            display_chat(delib_text, tab_delib)

    # Phase 3: Verdict
    with tab_verdict:
        with st.spinner("Preparing judgment..."):
            task_verdict = Task(
                description=f"""
                Deliver final Supreme Court judgment based on:
                Arguments: {args_text}
                Jury deliberation: {delib_text}
                Start with "Judgment Pronounced" as a heading.
                Then provide the full judgment using only the title "Presiding Judge" for all speaking parts.
                No emojis, no extra symbols, no additional text after the judgment.
                State clearly whether the appeal is allowed or dismissed and give the operative order.
                """,
                expected_output="Final judgment.",
                agent=judge
            )
            crew_verdict = Crew(agents=[judge], tasks=[task_verdict], process=Process.sequential, verbose=False)
            result_verdict = crew_verdict.kickoff()
            verdict_text = result_verdict.raw

            tab_verdict.markdown("**Judgment Pronounced**")
            display_chat(verdict_text, tab_verdict)