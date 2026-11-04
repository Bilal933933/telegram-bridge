from __future__ import annotations

import unittest

from bridge.presentation import screens
from bridge.presentation.markdown_to_html import to_html


class BlockquoteTests(unittest.TestCase):
    def test_quote_lines_become_a_blockquote(self) -> None:
        self.assertEqual(to_html("> a\n> b"), "<blockquote>a\nb</blockquote>")

    def test_inline_formatting_survives_inside_the_quote(self) -> None:
        self.assertIn("<b>x</b>", to_html("> **x**"))

    def test_quote_inside_a_code_block_is_untouched(self) -> None:
        html = to_html("```\n> raw\n```")
        self.assertIn("&gt; raw", html)
        self.assertNotIn("<blockquote>", html)

    def test_quote_and_plain_text_coexist(self) -> None:
        html = to_html("> q\nplain")
        self.assertEqual(html, "<blockquote>q</blockquote>\nplain")


class MessageBlockTests(unittest.TestCase):
    def test_user_message_is_quoted_and_labelled(self) -> None:
        block = screens._message_block({"type": "user", "text": "مرحبا"})
        self.assertEqual(block, "👤 **أنت**\n> مرحبا")

    def test_every_user_line_is_quoted(self) -> None:
        block = screens._message_block({"type": "user", "text": "a\nb"})
        self.assertTrue(block.endswith("> a\n> b"))

    def test_agent_message_is_plain_and_labelled(self) -> None:
        msg = {"type": "assistant",
               "content": [{"type": "text", "text": "تم"},
                           {"type": "tool", "tool": "bash"}]}
        block = screens._message_block(msg)
        self.assertTrue(block.startswith("🤖 **الوكيل**\nتم"))
        self.assertIn("bash", block)
        self.assertNotIn(">", block)

    def test_empty_messages_are_skipped(self) -> None:
        self.assertEqual(screens._message_block({"type": "user", "text": " "}), "")
        self.assertEqual(screens._message_block({"type": "assistant"}), "")

    def test_quote_keeps_blank_lines(self) -> None:
        self.assertEqual(screens.quote("a\n\nb"), "> a\n>\n> b")


class HistoryTextTests(unittest.TestCase):
    def test_history_separates_the_two_roles(self) -> None:
        text = screens.history([
            {"type": "user", "text": "سؤال"},
            {"type": "assistant", "content": [{"type": "text", "text": "جواب"}]},
        ])
        self.assertIn("👤 **أنت**\n> سؤال", text)
        self.assertIn("🤖 **الوكيل**\nجواب", text)
        self.assertEqual(text.count("**أنت**"), 1)

    def test_entries_separate_the_two_roles(self) -> None:
        text = screens.history_entries([
            {"role": "user", "text": "س"},
            {"role": "assistant", "text": "ج"},
        ])
        self.assertEqual(text, "👤 **أنت**\n> س\n\n🤖 **الوكيل**\nج")

    def test_entries_skip_empty_items(self) -> None:
        self.assertEqual(screens.history_entries([{"role": "user", "text": ""}]), "")


if __name__ == "__main__":
    unittest.main()
