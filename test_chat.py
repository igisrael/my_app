import sys
import codecs

# Force UTF-8 encoding for stdout
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

from dotenv import load_dotenv
load_dotenv()

from chatbot.agent import ChatbotAgent
import chatbot.agent

# Mock NLU to bypass API key errors
def mock_extract_intent(msg):
    if msg == 'שלום': return {"intent": "GREETING"}
    if msg == 'אני רותם מירון': return {"intent": "IDENTIFY_RESPONSE", "name": "רותם מירון"}
    if msg == 'הת.ז שלי היא 123456789': return {"intent": "IDENTIFY_RESPONSE", "id_number": "123456789"}
    if msg == 'מתי האימון שלי?': return {"intent": "APPOINTMENT_INQUIRY"}
    if msg == 'אני רותם': return {"intent": "IDENTIFY_RESPONSE", "name": "רותם"}
    if msg == '987654321': return {"intent": "IDENTIFY_RESPONSE", "id_number": "987654321"}
    if msg == 'אני עומר': return {"intent": "IDENTIFY_RESPONSE", "name": "עומר"}
    if msg == '111111111': return {"intent": "IDENTIFY_RESPONSE", "id_number": "111111111"}
    return {"intent": "OTHER"}

chatbot.agent.extract_intent = mock_extract_intent

agent = ChatbotAgent()
print('Testing normal authentication...')
print('Bot:', agent.process_message('שלום'))
print('Bot:', agent.process_message('אני רותם מירון'))
print('Bot:', agent.process_message('הת.ז שלי היא 123456789'))
print('Bot:', agent.process_message('מתי האימון שלי?'))

agent.state.reset()
print('\nTesting partial name authentication...')
print('Bot:', agent.process_message('אני רותם'))
print('Bot:', agent.process_message('987654321'))
print('Bot:', agent.process_message('מתי האימון שלי?'))

agent.state.reset()
print('\nTesting max attempts...')
print('Bot:', agent.process_message('אני עומר'))
print('Bot:', agent.process_message('111111111')) # wrong
print('Bot:', agent.process_message('111111111')) # wrong
print('Bot:', agent.process_message('111111111')) # wrong
print('State:', agent.state.stage)
