from lionel_types.page import Glyph, Page, layout, move_vertically, wrap

WHITE = (255, 255, 255)


def page_of(*paragraphs):
    page = Page()
    for i, text in enumerate(paragraphs):
        if i:
            page.new_paragraph()
        for ch in text:
            page.insert(Glyph(ch, WHITE))
    return page


def measure(glyph):
    return 10.0  # every glyph is 10px wide


def lay(page, max_width=100):
    return layout(page, measure, max_width, line_height=20, paragraph_gap=15, center=(500, 300))


def rows(text, max_width):
    return [text[a:b] for a, b in wrap([10] * len(text), [c == " " for c in text], max_width)]


def test_wrap_keeps_short_text_on_one_row():
    assert rows("hello", 100) == ["hello"]


def test_wrap_breaks_after_the_last_space_that_fits():
    assert rows("the cat sat", 70) == ["the ", "cat sat"]


def test_wrap_splits_a_word_too_long_for_a_row():
    assert rows("abcdefghij", 40) == ["abcd", "efgh", "ij"]


def test_wrap_gives_an_empty_paragraph_one_row():
    assert wrap([], [], 100) == [(0, 0)]


def test_rows_are_centered_and_the_block_is_vertically_centered():
    result = lay(page_of("abcd"))
    (line,) = result.lines
    assert line.left == 500 - 20  # 40px wide, centered on x=500
    assert result.height == 20
    assert line.top == 300 - 10


def test_enter_leaves_a_blank_gap_between_paragraphs():
    result = lay(page_of("ab", "cd"))
    first, second = result.lines
    assert second.top - first.top == 20 + 15
    assert result.height == 20 + 15 + 20


def test_backspace_deletes_then_joins_paragraphs():
    page = page_of("ab", "c")
    assert page.backspace().text == "c"
    assert page.backspace() is None  # joins with the paragraph above
    assert len(page.paragraphs) == 1
    assert page.backspace().text == "b"
    assert "".join(g.text for g in page.glyphs()) == "a"


def test_typing_in_the_middle_inserts_at_the_cursor():
    page = page_of("ac")
    page.move_left()
    page.insert(Glyph("b", WHITE))
    assert "".join(g.text for g in page.glyphs()) == "abc"


def test_left_and_right_cross_paragraphs():
    page = page_of("ab", "cd")
    page.set_cursor(1, 0)
    page.move_left()
    assert (page.para, page.index) == (0, 2)
    page.move_right()
    assert (page.para, page.index) == (1, 0)


def test_up_and_down_keep_the_cursor_near_the_same_x():
    page = page_of("abcdefgh", "abcd")  # rows 80px and 40px wide, both centered
    page.set_cursor(1, 2)  # middle of the short row: x = 500
    move_vertically(page, lay(page), -1)
    assert (page.para, page.index) == (0, 4)  # middle of the long row
    move_vertically(page, lay(page), 1)
    assert (page.para, page.index) == (1, 2)


def test_up_from_the_top_goes_to_the_start_and_down_from_the_bottom_to_the_end():
    page = page_of("abc", "de")
    page.set_cursor(0, 2)
    move_vertically(page, lay(page), -1)
    assert (page.para, page.index) == (0, 0)
    page.set_cursor(1, 0)
    move_vertically(page, lay(page), 1)
    assert (page.para, page.index) == (1, 2)


def test_cursor_at_a_wrap_point_sits_at_the_start_of_the_lower_row():
    page = page_of("abcdefgh")
    result = lay(page, max_width=40)
    x, top = result.cursor_position(0, 4)
    assert top == result.lines[1].top
    assert x == result.lines[1].left


def test_word_before_cursor_stops_at_non_letters():
    page = page_of("hi cat")
    assert page.word_before_cursor() == "cat"
    page.insert(Glyph("F1", WHITE, is_label=True))
    assert page.word_before_cursor() == ""
