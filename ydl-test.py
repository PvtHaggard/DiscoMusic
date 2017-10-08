import youtube_dl
# I found - https://www.youtube.com/watch?v=Yj6V_a1-EUA
# Playlist - https://www.youtube.com/watch?v=Yj6V_a1-EUA&list=RDYj6V_a1-EUA&t=6


ydl_opts = {
    'format': 'worstaudio',
    'outtmpl': '/cache/%(title)s.%(ext)s',
    'noplaylist': False
}

youtube_dl.YoutubeDL(ydl_opts).download(['www.youtube.com/watch?v=Yj6V_a1-EUA'])
