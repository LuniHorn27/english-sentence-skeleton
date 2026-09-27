"""片語測試：該找到的有找到、不該找到的沒找錯。

用法：.venv/bin/python tests/phrases_test.py
（考試題是封存的，不拿來調整片語清單。）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.analyzer.engine import get_nlp  # noqa: E402
from backend.analyzer.phrases import find_phrases, load_phrases  # noqa: E402

# （句子, 應該找到的片語 id 集合）；空集合＝一個都不該找到
CASES = [
    # 使用者回報、慣用語
    ("I give you a big hand.", {"give_a_big_hand"}),
    ("Let's give a big hand to our speaker.", {"give_a_big_hand_to"}),
    ("Can you give me a hand with these boxes?", {"give_a_hand"}),
    ("It's raining cats and dogs, so let's stay inside.", {"rain_cats_and_dogs"}),
    ("It rained cats and dogs yesterday.", {"rain_cats_and_dogs"}),
    ("Break a leg!", {"break_a_leg"}),
    ("I'm feeling a bit under the weather today.", {"under_the_weather"}),
    ("He let the cat out of the bag about the party.", {"let_the_cat_out_of_the_bag"}),
    ("The test was a piece of cake.", {"a_piece_of_cake"}),
    ("My grandson is the apple of my eye.", {"the_apple_of_one_s_eye"}),
    ("Are you pulling my leg?", {"pull_one_s_leg"}),
    # 動詞片語：連在一起、中間夾受詞、被動、疑問句
    ("She gave up smoking last year.", {"give_up"}),
    ("Don't give it up.", {"give_up"}),
    ("Please turn the lights off.", {"turn_off"}),
    ("Turn off the TV.", {"turn_off"}),
    ("The game was called off because of the rain.", {"call_off", "because_of"}),
    ("I am looking forward to seeing you.", {"look_forward_to"}),
    ("We ran out of milk.", {"run_out_of"}),
    ("I ran into an old friend.", {"run_into"}),
    ("What are you looking for?", {"look_for"}),
    ("Who will look after the baby?", {"look_after"}),
    ("He made up his mind to study abroad.", {"make_up_one_s_mind"}),
    ("Please take good care of your sister.", {"take_care_of"}),
    ("She put on her coat.", {"put_on"}),
    ("The experience turned him into a good student.", {"turn_sth_into"}),
    ("I get up at six every morning.", {"get_up"}),
    # 形容詞片語、介系詞片語
    ("She is very interested in music.", {"be_interested_in"}),
    ("He is good at math.", {"be_good_at"}),
    ("I am used to getting up early.", {"be_used_to", "get_up"}),
    ("In the long run, practice pays off.", {"in_the_long_run"}),
    ("There is a tree in front of my house.", {"in_front_of"}),
    # 不該找到的
    ("Please put the book on the table.", set()),
    ("He waited outside the stadium for several hours.", set()),
    ("I give you a book.", set()),
    ("The cat is in the bag.", set()),
    ("The weather is nice today.", set()),
    ("She looked at the moon.", set()),
    ("He took the book from the shelf.", set()),
    ("I used to play basketball.", set()),
    ("The dog ran out of the house.", {"run_out_of"}),  # 字面「跑出去」也會被找到：已在說明中提醒要看上下文
]

KNOWN_AMBIGUOUS = {"The dog ran out of the house."}  # 已知會找到、但意思其實是字面的例子


def main():
    nlp = get_nlp()
    load_phrases()
    fails = 0
    for text, expected in CASES:
        got = set()
        for sent in nlp(text).sents:
            got |= {p.id for p in find_phrases(sent)}
        ok = got == expected
        mark = "✓" if ok else "✗"
        if not ok:
            fails += 1
        extra = "（已知：字面意思也會被找到）" if text in KNOWN_AMBIGUOUS else ""
        print(f"{mark} {text}  →  {sorted(got) or '（無）'}{'' if ok else f'  應該是 {sorted(expected) or "（無）"}'}{extra}")
    print(f"\n{len(CASES) - fails}／{len(CASES)} 通過；片語清單共 {len(load_phrases())} 個")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
