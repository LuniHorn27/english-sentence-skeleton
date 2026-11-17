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
    ("In the long run, practice pays off.", {"in_the_long_run", "pay_off"}),
    ("There is a tree in front of my house.", {"in_front_of"}),
    # 2026-09-29 夜間新增的片語、慣用語、諺語
    ("An apparently small event may lead to a great result.", {"lead_to"}),
    ("You should take advantage of this chance.", {"take_advantage_of"}),
    ("I can't help laughing.", {"can_t_help"}),
    ("She burst into tears.", {"burst_into"}),
    ("Please calm down.", {"calm_down"}),
    ("Yanni tried to calm Skura down.", {"calm_down"}),
    ("He is completely absorbed in his book.", {"be_absorbed_in"}),
    ("This movie is based on a true story.", {"be_based_on"}),
    ("Tom was finally able to get in touch with Mary.", {"get_in_touch_with"}),
    ("It never crossed my mind.", {"cross_one_s_mind"}),
    ("We need to make good use of the money.", {"make_use_of"}),
    ("That has nothing to do with me.", {"have_nothing_to_do_with"}),
    ("I'm dealing with some problems at the moment.", {"at_the_moment", "deal_with"}),
    ("I keep a knife in my pocket at all times.", {"at_all_times"}),
    ("I didn't feel comfortable at all.", {"at_all"}),
    ("Let's call it a day.", {"call_it_a_day"}),
    ("It's time to hit the hay.", {"hit_the_hay"}),
    ("He passed the exam with flying colors.", {"with_flying_colors"}),
    ("The news came out of the blue.", {"out_of_the_blue"}),
    ("Stop beating around the bush.", {"beat_around_the_bush"}),
    ("I hope Tom is caught red-handed.", {"caught_red_handed"}),
    ("Where there's a will, there's a way.", {"where_there_is_a_will"}),
    ("Where there is a will, there is a way.", {"where_there_is_a_will"}),
    ("The early bird catches the worm.", {"early_bird_catches"}),
    ("Rome wasn't built in a day.", {"rome_not_built_in_a_day"}),
    ("Don't judge a book by its cover.", {"dont_judge_a_book"}),
    ("No pain, no gain.", {"no_pain_no_gain"}),
    ("Actions speak louder than words.", {"actions_speak_louder"}),
    ("A friend in need is a friend indeed.", {"friend_in_need"}),
    ("Practice makes perfect.", {"practice_makes_perfect"}),
    ("Two heads are better than one.", {"two_heads"}),
    ("The more, the merrier.", {"the_more_the_merrier"}),
    ("I feel like giving up.", {"feel_like", "give_up"}),
    # 不該找到的
    ("Please put the book on the table.", set()),
    ("He waited outside the stadium for several hours.", set()),
    ("I give you a book.", set()),
    ("The cat is in the bag.", set()),
    ("The weather is nice today.", set()),
    ("She looked at the moon.", set()),
    ("He took the book from the shelf.", set()),
    ("I used to play basketball.", set()),
    ("Tom put his hand over Mary's hand.", set()),  # hand 是名詞
    ("Let's go back up there.", set()),  # back 是副詞
    ("I really think we need to be honest with Tom.", set()),
    ("Two children are sitting on the fence.", set()),
    ("The dog ran out of the house.", set()),  # 字面「跑出房子」：方向介系詞＋地點，不是 run out of（2026-10-08）
    ("We ran out of milk.", {"run_out_of"}),
    ("She looked into the box.", set()),  # 字面「往盒子裡看」，不是 look into（調查）
    ("The children came out of the classroom.", set()),  # 字面「走出教室」，不是 come out（出版、出現）
    ("The police looked into the case.", {"look_into"}),  # 調查：case 不是地點
]

KNOWN_AMBIGUOUS = set()  # 已知會找到、但意思其實是字面的例子


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
