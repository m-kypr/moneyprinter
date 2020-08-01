import praw
reddit = praw.Reddit(client_id='G0sWd3t4MfZuqg', client_secret="pI-xHd4HnMe8TXHXtIV_SHQH5ig",
                     password='NCC1062A', user_agent='Mozilla/5.0',
                     username='redditbantix')

subr = reddit.subreddit('xqcow')
r = subr.submit(title='LOL', url='https://www.google.com/')
print(r)
