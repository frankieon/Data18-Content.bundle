# Data18-Content
import re
import random
from datetime import datetime

# this code was borrowed from the Excalibur Films Agent. April 9 2013
# URLS
VERSION_NO = '1.2015.03.28.2'
EXC_BASEURL = 'http://www.data18.com/'
EXC_SEARCH_MOVIES = EXC_BASEURL + 'search/?k=%s&t=0'
EXC_MOVIE_INFO = EXC_BASEURL + 'content/%s'
USER_AGENT = 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.2;\ Trident/4.0;\
                 SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729;\
                 .NET CLR 3.0.30729; Media Center PC 6.0)'

titleFormats = r'DVD|Blu-Ray|BR|Combo|Pack'

XPATHS = {
    # Search Result Xpaths
    'scene-container': '//div[contains(@class,"bscene")]',
    'scene-link': '//span//a[contains(@href,"content")]',
    'scene-site': '//p[contains(text(), "Site")]]',
    'scene-network': '//p[contains(text(), "Network")]]',
    'scene-cast': '//p[contains(text(), "Cast")]]',

    # Actor in site Search results
    'site-link': '//select//Option[text()[contains(\
                        translate(., "$u", "$l"), "$s")\
                        ]]//@value',
    'actor-site-link': '//a[text()[contains(\
                            translate(., "$u", "$l"), "$s")\
                            ]]//@href',
    # Content Page Xpaths
    'release-date': '//p[text()[contains(\
                        translate(.,"relasdt","RELASDT"),\
                        "RELEASE DATE")]]//a',
    'release-date2': '//*[b[contains(text(),"Scene Information")]]\
                        //a[@title="Show me all updates from this date"]',
    'poster-image': '//img[@alt="poster"]',
    'single-image-url': '//img[contains(@alt,"image")]/..'
}


def Start():
    HTTP.CacheTime = CACHE_1DAY
    HTTP.SetHeader('User-agent', USER_AGENT)


def parse_content_date(date):
    try:
        return Datetime.ParseDate(date).date()
    except:
        return datetime.strptime(date, '%B %d, %Y').date()


def parse_document_date(html):
    date_found = None
    try:
        date_found = html.xpath(XPATHS['release-date'])[0].get('href')
        date_found_group = re.search(r'(\d{8})', date_found)
        date_found = date_found_group.group(0)
    except:
        date_found = html.xpath(XPATHS['release-date2'])[0].text_content()
    return parse_content_date(date_found)


def parse_search_results(results, search_results, media_title, year):
    count = 0
    title_lowercase = media_title.lower()
    for movie in search_results.xpath(XPATHS['scene-container']):

        title_link = movie.xpath(XPATHS['scene-link'])[0]
        movie_HREF = title_link.get("href").strip()
        Log('Movie HREF: ' + movie_HREF)

        current_name = title_link.text_content().strip()
        name_lowercase = current_name.lower()
        Log('New title: ' + current_name + ' ' + name_lowercase)

        current_ID = title_link.get('href').split('/', 4)[4]
        Log('New ID: ' + current_ID)

        name_distance_score = Util.LevenshteinDistance(title_lowercase,
                                                       name_lowercase)
        Log('Name Matching Distance', name_distance_score)

        # Start the score
        score = 100 - name_distance_score

        try:
            current_date = movie.xpath('/text()[1]')
            current_date = parse_content_date(current_date)
            Log('New Date: ' + str(current_date))
        except:
            try:
                movieResults = HTML.ElementFromURL(movie_HREF)
                current_date = parse_document_date(movieResults)
                Log('Found Date = ' + str(current_date))
            except (IndexError):
                Log('Date: No date found (Exception)')

        try:
            score = score - Util.LevenshteinDistance(year, current_date.year)
        except:
            pass

        if score >= 45:
            if current_name.count(', The'):
                current_name = 'The ' + current_name.replace(', The', '', 1)
            if current_date:
                current_name = current_name + ' [' + current_date + ']'

            Log('Found:')
            Log('    Date: ' + current_date)
            Log('    ID: ' + current_ID)
            Log('    Title: ' + current_name)
            Log('    URL: ' + movie_HREF)
            results.Append(MetadataSearchResult(id=current_ID,
                                                name=current_name,
                                                score=score,
                                                lang=lang))
        count += 1
    return count, results


def xpath_prepare(xpath, search):
    xpath = xpath.replace("$u", search.upper())
    xpath = xpath.replace("$l", search.lower())
    xpath = xpath.replace("$s", search.lower())
    return xpath


def find_site_url(siteURL, search_results, search):
    xp = xpath_prepare(XPATHS['site-link'], search)

    Log('xPath: ' + xp)
    try:
        siteURL = search_results.xpath(xp)[0]
    except:
        try:
            # If we failed, let's try with all elements lowercased
            xp = xpath_prepare(XPATHS['site-link'].lower(), search)
            Log('xPath: ' + xp)
            siteURL = search_results.xpath(xp)[0]
        except:
            search = re.sub(r'[\'\"]', '', search)
            xp = xpath_prepare(XPATHS['site-link'], search)
            # Let's try another iteration with less special characters
            try:
                siteURL = search_results.xpath(xp)[0]
            except:
                # If we failed, let's try with all elements lowercased
                xp = xpath_prepare(XPATHS['site-link'].lower(), search)
                Log('xPath: ' + xp)
                siteURL = search_results.xpath(xp)[0]
    return siteURL


def search_actor_in_site(results, media_title, year, lang):
    """
    Since Actor in Site scenes are not appearing in the search we need to
    find the actor's page, then find the site link, in order to find the actual
    content page.
    """

    Log('Alternative search for Actor in Site')

    # Should be used at a later point of the future of this parser
    # actors = media_title.split(' in ')[0].split(',')
    actors_url_parts = media_title.split(' in ')[0].lower()
    actors_url_parts = actors_url_parts.replace(' ', '_').split(',')
    site_name = media_title.split(' in ', 1)[1]
    Log('Search URL: ' + site_name)

    # Take the first actor and the website name to search
    query_actor = actors_url_parts[0].replace('-', '')
    query_actor = String.StripDiacritics(query_actor)
    query_actor = String.URLEncode(query_actor)
    searchURL = EXC_BASEURL + query_actor
    Log('Search URL: ' + searchURL)

    try:
        search_results = HTML.ElementFromURL(searchURL)
    except:
        # These are actors that do not have their page flushed out
        searchURL = EXC_BASEURL + 'dev/' + query_actor
        Log('Search URL: ' + searchURL)
        search_results = HTML.ElementFromURL(searchURL)

    try:
        searchURL = find_site_url(searchURL, search_results, site_name)
    except:
        search_results = HTML.ElementFromURL(searchURL + '/sites/')
        xp = xpath_prepare(XPATHS['actor-site-link'], site_name)
        Log('xPath: ' + xp)
        searchURL = search_results.xpath(xp)[0]

    search_results = HTML.ElementFromURL(searchURL)

    Log('Search URL: ' + searchURL)

    count, newResults = parse_search_results(results,
                                             search_results,
                                             media_title,
                                             year)
    results.Sort('score', descending=True)


class EXCAgent(Agent.Movies):
    name = 'Data18-Content'
    languages = [Locale.Language.English]
    accepts_from = ['com.plexapp.agents.localmedia']
    primary_provider = True

    def search(self, results, media, lang):
        Log('Data18 Version : ' + VERSION_NO)
        Log('**************SEARCH****************')
        title = media.name
        content_id = False

        if media.name.isdigit():
            Log('Media.name is numeric')
            content_id = True
            contentURL = EXC_MOVIE_INFO % media.name
            html = HTML.ElementFromURL(contentURL)
            title = html.xpath('//div/h1/text()')[0]
            results.Append(MetadataSearchResult(id=media.name,
                                                name=title,
                                                score='100',
                                                lang=lang))

        if media.primary_metadata is not None:
            title = media.primary_metadata.title

        year = media.year
        if media.primary_metadata is not None:
            year = media.primary_metadata.year
            Log('Searching for Year: ' + year)

        Log('Searching for Title: ' + title)

        if len(results) == 0:
            query = String.URLEncode(String.StripDiacritics(title))

            searchUrl = EXC_SEARCH_MOVIES % query
            Log('search url: ' + searchUrl)
            searchResults = HTML.ElementFromURL(searchUrl)
            searchTitle = searchResults.xpath('//title')[0].text_content()
            count, newResults = parse_search_results(results,
                                                     searchResults,
                                                     title,
                                                     year)

        if " in " in title.lower() and not content_id:
            try:
                search_actor_in_site(results, title, year, lang)
            except (IndexError):
                pass

        results.Sort('score', descending=True)

    def update(self, metadata, media, lang):
        Log('Data18 Version : ' + VERSION_NO)
        Log('**************UPDATE****************')
        contentURL = EXC_MOVIE_INFO % metadata.id
        html = HTML.ElementFromURL(contentURL)
        metadata.title = re.sub(titleFormats, '', media.title).strip(' .-+')

        Log('Current:')
        Log('    Title: ' + metadata.title)
        Log('    ID: ' + metadata.id)
        Log('    Release Date: ' + str(metadata.originally_available_at))
        Log('    Year: ' + str(metadata.year))
        Log('    URL: ' + contentURL)
        for key in metadata.posters.keys():
            Log('    PosterURLs: ' + key)

        # Release Date
        try:
            curdate = parse_document_date(html)
            metadata.originally_available_at = curdate
            curdate = str(curdate)
            metadata.year = metadata.originally_available_at.year

            # Commenting for now as this replaces the search title with no
            # date, which is helpful
            #metadata.title = re.sub(r'\[\d+-\d+-\d+\]', '',\
            #                               metadata.title).strip(' ')
            #Log('Title Updated')
            Log('Release Date Sequence Updated')
        except:
            pass

        # Get Poster
        # Get Official Poster if available
        i = 1

        try:
            posterimg = html.xpath(XPATHS['poster-image'])[0]
            posterUrl = posterimg.get('src').strip()
            Log('Official posterUrl: ' + posterUrl)
            posterRequest = HTTP.Request(posterUrl,
                                         headers={'Referer': contentURL})
            metadata.posters[posterUrl] = Proxy.Media(posterRequest.content,
                                                      sort_order=i)
            i += 1
            Log('Poster Sequence Updated')
        except:
            pass

        # Get First Photo Set Pic if available
        try:
            photoSetIndex = 0
            imageURL =  html.xpath(XPATHS['single-image-url'])[photoSetIndex]
            imageURL = imageURL.get('href')

            imagehtml = HTML.ElementFromURL(imageURL)

            posterimg = imagehtml.xpath('//img[@alt= "image"]')[0]
            posterUrl = posterimg.get('src').strip()
            Log('imageUrl: ' + posterUrl)
            metadata.posters[posterUrl] = Proxy.Media(HTTP.Request(posterUrl, headers={'Referer': imageURL}).content, sort_order = i)
            i += 1
            #Random PhotoSet image incase first image isn't desired
            photoSetIndex = random.randint(1,len(html.xpath('//img[contains(@alt,"image")]/..'))-1)
            imageURL =  html.xpath('//img[contains(@alt,"image")]/..')[photoSetIndex].get('href')
            imagehtml = HTML.ElementFromURL(imageURL)
            posterimg = imagehtml.xpath('//img[@alt= "image"]')[0]
            posterUrl = posterimg.get('src').strip()
            Log('imageUrl: ' + posterUrl)
            metadata.posters[posterUrl] = Proxy.Media(HTTP.Request(posterUrl, headers={'Referer': imageURL}).content, sort_order = i)
            i += 1
            Log('Poster - Photoset - Sequence Updated')
        except:
            pass

        # Get First Photo Set Pic if available (when src is used instead of href)
        try:
            photoSetIndex = 0
            posterimg = html.xpath('//img[contains(@alt,"image")]')[photoSetIndex]
            posterUrl = posterimg.get('src').strip()
            Log('imageUrl: ' + posterUrl)
            metadata.posters[posterUrl] = Proxy.Media(HTTP.Request(posterUrl, headers={'Referer': contentURL}).content, sort_order = i)
            i += 1
            #Random PhotoSet image incase first image isn't desired
            photoSetIndex = random.randint(1,len(html.xpath('//img[contains(@alt,"image")]'))-1)
            posterimg = html.xpath('//img[contains(@alt,"image")]')[photoSetIndex]
            posterUrl = posterimg.get('src').strip()
            Log('imageUrl: ' + posterUrl)
            metadata.posters[posterUrl] = Proxy.Media(HTTP.Request(posterUrl, headers={'Referer': contentURL}).content, sort_order = i)
            i += 1
            Log('Poster - Photoset - Sequence Updated')
        except:
            pass

        # Get alternate Poster - Video
        try:
            posterimg = html.xpath('//img[@alt="Play this Video"]')[0]
            posterUrl = posterimg.get('src').strip()
            Log('Video Postetr Url: ' + posterUrl)
            metadata.posters[posterUrl] = Proxy.Media(HTTP.Request(posterUrl, headers={'Referer': contentURL}).content, sort_order = i)
            Log('Video Poster Sequence Updated')
        except:
            pass

        # Get Art
        # Get Art from "Play this Video"
        try:
            i = 1
            posterimg = html.xpath('//img[@alt="Play this Video"]')[0]
            posterUrl = posterimg.get('src').strip()
            Log('ArtUrl: ' + posterUrl)
            metadata.art[posterUrl] = Proxy.Media(HTTP.Request(posterUrl, headers={'Referer': contentURL}).content,  sort_order = i)
            i += 1
            Log('Art Sequence Updated')
        except:
            pass
        #Second try at "Play this Video" (Embedded html #document)
        try:
            imageURL =  html.xpath('//*//iframe[contains(@src,"player.php")][1]')[0].get('src')
            imagehtml = HTML.ElementFromURL(imageURL)
            posterimg = imagehtml.xpath('//img[@alt="Play this Video"]')[0]
            posterUrl = posterimg.get('src').strip()
            Log('imageUrl: ' + posterUrl)
            metadata.art[posterUrl] = Proxy.Media(HTTP.Request(posterUrl, headers={'Referer': imageURL}).content, sort_order = i)
            i += 1
            Log('Art -Embedded Video- Sequence Updated')
        except:
            pass

        # Get First Photo Set Pic if available
        try:
            photoSetIndex = 0
            imageURL =  html.xpath('//img[contains(@alt,"image")]/..')[photoSetIndex].get('href')
            imagehtml = HTML.ElementFromURL(imageURL)
            posterimg = imagehtml.xpath('//img[@alt= "image"]')[0]
            posterUrl = posterimg.get('src').strip()
            Log('imageUrl: ' + posterUrl)
            metadata.art[posterUrl] = Proxy.Media(HTTP.Request(posterUrl, headers={'Referer': imageURL}).content, sort_order = i)
            i += 1
            #Random PhotoSet image incase first image isn't desired
            photoSetIndex = random.randint(1,len(html.xpath('//img[contains(@alt,"image")]/..'))-1)
            imageURL =  html.xpath('//img[contains(@alt,"image")]/..')[photoSetIndex].get('href')
            imagehtml = HTML.ElementFromURL(imageURL)
            posterimg = imagehtml.xpath('//img[@alt= "image"]')[0]
            posterUrl = posterimg.get('src').strip()
            Log('imageUrl: ' + posterUrl)
            metadata.art[posterUrl] = Proxy.Media(HTTP.Request(posterUrl, headers={'Referer': imageURL}).content, sort_order = i)
            i += 1
            Log('Art - Photoset - Sequence Updated')
        except:
            pass

        # Get First Photo Set Pic if available (when src is used instead of href)
        try:
            photoSetIndex = 0
            posterimg = html.xpath('//img[contains(@alt,"image")]')[photoSetIndex]
            posterUrl = posterimg.get('src').strip()
            Log('imageUrl: ' + posterUrl)
            metadata.art[posterUrl] = Proxy.Media(HTTP.Request(posterUrl, headers={'Referer': contentURL}).content, sort_order = i)
            i += 1
            #Random PhotoSet image incase first image isn't desired
            photoSetIndex = random.randint(1,len(html.xpath('//img[contains(@alt,"image")]'))-1)
            posterimg = html.xpath('//img[contains(@alt,"image")]')[photoSetIndex]
            posterUrl = posterimg.get('src').strip()
            Log('imageUrl: ' + posterUrl)
            metadata.art[posterUrl] = Proxy.Media(HTTP.Request(posterUrl, headers={'Referer': contentURL}).content, sort_order = i)
            i += 1
            Log('Poster - Photoset - Sequence Updated')
        except:
            pass

        # Genre.
        try:
            metadata.genres.clear()
            genres = html.xpath('//*[b[contains(text(),"Categories")]]//a[contains(@href, ".html")]')
            if len(genres) > 0:
                for genreLink in genres:
                    genreName = genreLink.text_content().strip('\n')
                    if len(genreName) > 0 and re.match(r'View Complete List', genreName) is None:
                        if re.match(r'Filter content by multiple tags', genreName) is None:
                            metadata.genres.add(genreName)
            Log('Genre Sequence Updated')
        except:
            pass

        # Summary.
        try:
            metadata.summary = ""
            paragraph = html.xpath('//*[b[contains(text(),"Story:")]]')[0]
            metadata.summary = paragraph.text_content().replace('&13;', '').strip(' \t\n\r"') + "\n"
            metadata.summary.strip('\n')
            metadata.summary = re.sub(r'Story: \n','',metadata.summary)
            Log('Summary Sequence Updated')
        except:
            pass

        # Starring
        starring = html.xpath('//*[b[contains(text(),"Starring:")]]//a[@class="bold"]')
        metadata.roles.clear()
        for member in starring:
        try:
            role = metadata.roles.new()
            role.actor = member.text_content().strip()
            photo = member.get('href').strip()
            photohtml = HTML.ElementFromURL(photo)
            role.photo = html.xpath('//a[@href="' + photo + '"]//img')[0].get('src')
            Log('Member Photo Url : ' + role.photo)
        except:
            pass
        Log('Starring Sequence Updated')

        # Studio
        try:
            metadata.studio = html.xpath('//a[contains(@href,"http://www.data18.com/sites/") and following-sibling::i[position()=1][text()="Network"]]')[0].text_content().strip()
            Log('Studio Sequence Updated')
        except:
            pass

        # Collection
        try:
            collection = html.xpath('//a[contains(@href,"http://www.data18.com/sites/") and following-sibling::i[position()=1][text()="Site"]]')[0].text_content().strip()
            metadata.collections.clear()
            metadata.collections.add(collection)
            Log('Collection Sequence Updated')
        except:
            pass

        # Tagline
        try:
            metadata.tagline = contentURL #html.xpath('//a[@href="http://www.data18.com/sites/"]/following-sibling::a[last()]')[0].get('href')
            Log('Tagline Sequence Updated')
        except:
            pass

        # Content Rating
        metadata.content_rating = 'NC-17'

        Log('Updated:')
        Log('    Title:...............' + metadata.title)
        Log('    ID:..................' + metadata.id)
        Log('    Release Date:........' + str(metadata.originally_available_at))
        Log('    Year:................' + str(metadata.year))
        Log('    TagLine:.............' + str(metadata.tagline))
        Log('    Studio:..............' + str(metadata.studio))

        try:
            for key in metadata.posters.keys():
                Log('    PosterURLs:..........' + key)
        except:
            pass
        try:
            for key in metadata.art.keys():
                Log('    BackgroundArtURLs:...' + key)
        except:
            pass
        try:
            for x in range(len(metadata.collections)):
                Log('    Network:.............' + metadata.collections[x])
        except:
            pass
        try:
            for x in range(len(metadata.roles)):
                Log('    Starring:............' + metadata.roles[x].actor)
        except:
            pass

        try:
            for x in range(len(metadata.genres)):
                Log('    Genres:..............' + metadata.genres[x])
        except:
            pass
