"""Phase 7: small, repeatable golden-question benchmark."""
import json
from uuid import uuid4
from config import ROOT
from agent_factory import open_agent
from agent_runner import ask
from trace_helpers import flush_traces


def main():
    dataset = json.loads((ROOT / 'golden_questions.json').read_text(encoding='utf-8'))
    passed = 0
    with open_agent(user_id='eval-demo') as agent:
        for case in dataset:
            result = ask(agent, case['question'], thread_id=uuid4().hex, user_id='eval-demo')
            used = {t['name'] for t in result['tools']}
            expected = set(case.get('expected_tools', []))
            ok = expected.issubset(used)
            passed += int(ok)
            print(f"{'PASS' if ok else 'CHECK'}: {case['question']}")
            print(f"  expected tools: {sorted(expected)}; used: {sorted(used)}")
            print(f"  time: {result['latency_ms']} ms; tokens reported: {result['tokens_reported']}")
            print(f"  answer: {result['answer'][:160]}")
    print(f'Expected tool coverage: {passed}/{len(dataset)}')
    print('NOTE: Tool coverage is NOT full answer-quality evaluation. Review groundedness manually.')
    flush_traces()

if __name__ == '__main__':
    main()
