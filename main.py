import eyed3 as eyed3
import praw
import json
import random
from pydub import AudioSegment
import os
from azure.cognitiveservices.speech import SpeechConfig, SpeechSynthesizer
from azure.cognitiveservices.speech.audio import AudioOutputConfig
import subprocess
import string
from datetime import datetime
import time
import re

print("Starting episode generation....")


with open('./settings.json') as f:
    settings = json.load(f)

reddit = praw.Reddit(
    client_id=settings["reddit"]["client_id"],
    client_secret=settings["reddit"]["client_secret"],
    user_agent=settings["reddit"]["user_agent"]
)


def add_to_used(post_id):
    used_list = open("list.txt", "a")
    used_list.write(post_id + "\n")
    used_list.close()


def is_used(post_id):
    used_list = open('list.txt', 'r')
    used_list = used_list.readlines()
    return str(post_id) + "\n" in used_list


def process_text(text):
    pattern = r'(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([' \
              r'^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’]))'
    match = re.findall(pattern, text)
    for m in match:
        url = m[0]
        text = text.replace(url, ' LINK ')
    text = re.sub(r'\w+:\/{2}[\d\w-]+(\.[\d\w-]+)*(?:(?:\/[^\s/]*))*', '', text)
    text = re.sub(r'^https?:\/\/.*[\r\n]*', '', text, flags=re.MULTILINE)

    text = text.replace("&#x200b", " ")
    text = text.replace("&#x200B", " ")
    text = text.replace("#x200b", "")

    text = text.replace("\n", " ")
    text = text.replace("_", " ")
    text = text.replace("\\", " ")
    text = text.replace("*", " ")

    text = text.replace(".", " . ")
    return text



def get_speech_config():
    # create azure speech config
    speech_config = SpeechConfig(subscription=settings["azure"]["key"], region=settings["azure"]["region"])

    # set azure voice
    speech_config.speech_synthesis_language = "en-GB"
    speech_config.speech_synthesis_voice_name = "en-GB-RyanNeural"
    return speech_config


def voice(post_text, current_number):
    print("voicing: " + post_text)
    print("number: " + str(current_number))
    speech_config = get_speech_config()
    audio_config = AudioOutputConfig(filename="./" + str(current_number) + ".wav")
    synth = SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    synth.speak_text_async(post_text)


def voice_introduction(text):
    speech_config = get_speech_config()

    audio_config = AudioOutputConfig(filename="./introduction.wav")
    synthesizer = SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    synthesizer.speak_text_async(text)


def combined_audio_files(post_amount):
    introduction = AudioSegment.from_wav("introduction.wav")
    combined = introduction
    current_number = 0
    while current_number != post_amount:
        current_number += 1
        combined += AudioSegment.from_wav(str(current_number) + ".wav")

    combined.export("episode.wav", format="wav")


def convert_to_mp3():
    wav = 'episode.wav'
    cmd = 'lame --preset extreme %s' % wav
    subprocess.call(cmd, shell=True)


def delete_old_files():
    for item in os.listdir("./"):
        if item.endswith(".wav"):
            os.remove(os.path.join("./", item))


def get_random_string():
    return ''.join(random.choice(string.ascii_lowercase) for i in range(10))


def move_mp3(mp3_name):
    os.rename("episode.mp3", "./public/media/" + mp3_name + ".mp3")


def add_episode(subreddit, mp3_name, episode_credits):
    feed_file = open('public/feed.xml', 'r')
    feed = feed_file.readlines()
    feed_file.close()
    del feed[-2:]

    title = "r/" + subreddit + " | daily reddit podcast"

    pubDate = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z") + " GMT"

    mp3_link = "https://reddit.cast.exonip.de/media/" + mp3_name + ".mp3"

    time_length = time.strftime('%H:%M:%S',
                                time.gmtime(eyed3.load("./public/media/" + mp3_name + ".mp3").info.time_secs))

    byte_size = str(os.path.getsize("./public/media/" + mp3_name + ".mp3"))

    feed.append("<item>" + "\n")
    feed.append("<title>" + title + "</title>" + "\n")
    feed.append("<itunes:subtitle>" + title + "</itunes:subtitle>" + "\n")
    feed.append("<description>Credits: " + "\n" + episode_credits + "</description>" + "\n")
    feed.append("<link>" + mp3_link + "</link>" + "\n")
    feed.append('<enclosure url="' + mp3_link + '" length="' + byte_size + '" type="audio/mpeg"/>' + "\n")
    feed.append("<guid>" + mp3_link + "</guid>" + "\n")
    feed.append("<itunes:duration>" + time_length + "</itunes:duration>" + "\n")
    feed.append("<author>reddit.cast@exonip.de (Exonip)</author>" + "\n")
    feed.append("<itunes:author>Exonip</itunes:author>" + "\n")
    feed.append("<itunes:explicit>no</itunes:explicit>" + "\n")
    feed.append('<itunes:image href="https://reddit.cast.exonip.de/images/itunes_image.jpg"/>' + "\n")
    feed.append("<pubDate>" + pubDate + "</pubDate>" + "\n")
    feed.append("</item>" + "\n")
    feed.append("</channel>" + "\n")
    feed.append("</rss>" + "\n")

    feed_file = open("public/feed.xml", "w")
    feed_file.writelines(feed)
    feed_file.close()


# select subreddit
subreddits = settings["subreddits"]

subreddit = subreddits[random.randint(0, (len(subreddits) - 1))]

print("Selected random subreddit: " + subreddit)

print("Generating introduction...")

text = settings["introduction"] + subreddit + " . "

print("Introduction: " + text)

print("Voiceing introduction...")
voice_introduction(text)


post_amount = random.randint(4, 12)

print("Random post amount: " + str(post_amount))
current_number = 0
episode_credits = ""

while True:
    if current_number == post_amount:
        break
    for submission in reddit.subreddit(subreddit).top():
        if current_number == post_amount:
            break
        print("Found post \"" + submission.title + "\" with id " + submission.id + "...")

        if is_used(submission.id) or len(submission.selftext) < 100:
            print("Post to short or already used!")
            continue
        print("Adding post...")
        add_to_used(submission.id)
        current_number += 1

        try:
            username = submission.author.name
            title = submission.title
            content = submission.selftext
            if current_number == 1:
                template_text = settings["first-post-announcement"]
            elif current_number is post_amount - 1:
                template_text = settings["last-post-announcement"]
            else:
                template_text = settings["next-post-announcement"]
            text = template_text.replace("$USERNAME", username).replace("$TITLE", title).replace("$CONTENT", content)
        except AttributeError:
            continue
        text = process_text(text)
        print ("text:" + text)
        print("processed text")
        voice(text, current_number)
        try:
            episode_credits += '"' + submission.title + '"' + " by u/" + submission.author.name + ": " + submission.url + "\n "
        except AttributeError:
            episode_credits += submission.title + " : " + submission.url + "\n"

combined_audio_files(post_amount)

convert_to_mp3()

delete_old_files()

mp3_name = get_random_string()

move_mp3(mp3_name)

add_episode(subreddit, mp3_name, episode_credits)
