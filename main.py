import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.exceptions import TelegramBadRequest
oh
from aiogram.filters.command import Command
import aiohttp
import urllib.parse
from typing import Dict, List, Optional
from config_reader import config

logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.bot_token.get_secret_value(), default=DefaultBotProperties(parse_mode="html"))
dp = Dispatcher()

class StaticData:
    last_tags = None

def combine_tags(tags: Dict[str, List[str]]) -> List[str]:
    result: List[str] = []

    for tag_category in tags.values():
        tag_category: List[str]
        result.extend(tag_category)
    
    return result


# @dp.message(Command("furr"))
# async def cmd_fur(message: types.Message):
#     command = message.text.split(" ", 1)
#     if len(command) <= 1:
#         await message.reply("Expected to see amount of posts to fetch.")
#         return
#     if len(command) <= 2:
#         await message.reply("Expected to see tags.")
#         return

def beautify_link(url: Optional[str]):
    if url is None:
        return "Unknown"

    try:
        parsed = urllib.parse.urlparse(url)
        return f'<a href="{url}">{parsed.hostname.rsplit(".", 1)[0].split(".")[-1].title()}</a>'
    except AttributeError:
        return url


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.reply((
        f"Commands:"
        f"\n- <code>/fur &lt;Tags&gt;</code> | Lookup a random post with given tags"
        f"\n- <code>/furl</code> | Lookup a random post with previously given tags from <code>/fur</code>"
        f"\n\n🇷🇺 <code>2200 7008 6671 1137</code>"
        f'\n💎 <a href="https://t.me/send?start=IVpmagfZBT5P">Cryptobot</a>'
    ))

@dp.message(Command("furl"))
async def cmd_furl(message: types.Message):
    if not StaticData.last_tags:
        await message.reply("I dont know any tags yet.")
        return

    return await cmd_fur(message, StaticData.last_tags)


@dp.message(Command("fur"))
async def cmd_fur(message: types.Message, bypass_query: Optional[str] = None):
    query = bypass_query
    if not bypass_query:
        command = message.text.split(" ", 1)
        if len(command) <= 1:
            await message.reply("Expected to see tags.")
            return
        query = urllib.parse.quote(command[-1]).replace("%20", "+")

    async with aiohttp.ClientSession(headers={"User-Agent": "t.me/e621csbot"}) as session:
        async with session.get(f"https://e621.net/posts.json?tags=order%3Arandom+{query}+-gore+-scat+-watersports+-young+-loli+-shota+-digestion+-hyper+-overweight&limit=1") as response:
            if response.status >= 300:
                await message.reply(f"Got {response.status}.")
                return

            json = await response.json()
            posts: List[dict] = json["posts"]
            if len(posts) <= 0:
                await message.reply("No posts found.")
                return
            post: dict = posts[0]

            is_flash: bool = post["file"]["ext"] == "swf"
            is_photo: bool = post["file"]["ext"] in ["png", "jpg", "jpeg"]
            is_video: bool = "animated" in post["tags"]["meta"]
            is_nsfw: bool = post["rating"] != "s"

            sources_formatted: str = ", ".join(map(beautify_link, post["sources"]))
            rating_emoji: str = {"s": "🟢", "q": "🟡", "e": "🔴"}[post["rating"]]
            artists: List[str] = post["tags"]["artist"]

            caption: str = (
                f'{rating_emoji} <a href="https://e621.net/posts/{post["id"]}">{post["id"]}</a>'
                f"\nArtist{'s' if len(artists) > 1 else ''}: <b>{', '.join(artists)}</b>"
                + (f"\nSources: {sources_formatted}" if sources_formatted else "") +
                "\n\n<blockquote expandable>Tags:"
                f"\n\nGeneral ({len(post['tags']['general'])}):\n{', '.join(post['tags']['general'])}"
                f"\n\nCopyright ({len(post['tags']['copyright'])}):\n{', '.join(post['tags']['copyright'])}"
                f"\n\nCharacter ({len(post['tags']['character'])}):\n{', '.join(post['tags']['character'])}"
                f"\n\nSpecies ({len(post['tags']['species'])}):\n{', '.join(post['tags']['species'])}"
                f"\n\nMeta ({len(post['tags']['meta'])}):\n{', '.join(post['tags']['meta'])}"
                f"\n\nLore ({len(post['tags']['lore'])}):\n{', '.join(post['tags']['lore'])}"
                "</blockquote>"
            )

            if is_flash:
                await message.reply(f"Flash not supported.\n\n{caption}")
                return
            
            StaticData.last_tags = query

            try:
                if is_photo:
                    await message.reply_photo(post["file"]["url"], has_spoiler=is_nsfw, caption=caption)
                elif is_video:
                    await message.reply_video(post["file"]["url"], has_spoiler=is_nsfw, caption=caption)
                else:
                    await message.reply_document(post["file"]["url"], has_spoiler=is_nsfw, caption=caption)
            except TelegramBadRequest:
                return await cmd_fur(message)


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
