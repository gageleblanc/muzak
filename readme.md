# Muzak (music organizer)

Muzak is a tool I created over a couple weekends for managing my growing local music library. I've noticed that between old music I had saved already and newer music coming from various sources (Digital download, old CDs, etc.), the directory structure and file naming scheme can be vastly different. For media library mangement tools like Plex, it is best to store files in certain formats for optimal library scanning performance and accuracy, and manually renaming/moving these files became a lot of work. Muzak is mainly built to organize and query your music library and music you want to add to your library. Muzak can very quickly scan your files and gather ID3 tags, and then copy or move them to another location (or the same location, if you desire), based on those tags. Currently, Muzak is only a command-line application, however I have spent some time working on a GUI implementation as well.

Muzak is simple to use, you can `pip install muzak` and get started by setting a storage directory with `muzak config set storage_directory <target directory>`. Once you have a storage directory, you can use `muzak operator rescan-storage` to re-scan the currently configured storage directory and add any new files to Muzak. To scan and organize another directory, you can use `muzak organize` or `muzak scan` and then `muzak organize-cache`. Organization commands accept a --move argument which will move the files from the source to the destination, and `organize` will automatically remove empty directories after scanning and moving music. 

You can customize the path format that Muzak uses to store your files by changing the output_format configuration value. Accepted values are labels enclosed in lt/gt symbols, i.e. `<artist>`. The default format is: `<artist>/<album>/<title>`, where forward slashes are directory separators. 

Once you have some music in Muzak, you can use `muzak query` with the --query argument, or use the interactive query prompt to query your music based on the ID3 tag labels that Muzak has detected. For example, to show the artist, album and title of every track with the genre of "Punk", you could run the following query: `SELECT [artist, album, title] WHERE {genre=Punk}`. Note that `LIMIT` syntax is supported as well. You may query for the labels that Muzak is aware of by running `SHOW labels`, and you can show a list of all available properties with `SHOW properties`. 

You can also use Muzak queries to update the tags on your music files. For example, a lot of Punk music has the incorrect "Genre" tag. Update syntax requires a key=>value pairing where you would normally put your list of labels to select. An example would look something like this: `UPDATE &{genre=Punk} WHERE {album=Rpm10}`. Notice the ampersand token before the beginning of your key->value pairing. This is necessary to ensure the values you give are properly parsed and mapped internally. Key=>Value mappings without the ampersand character are considered "eager," which is used when matching tracks during a SELECT query, in order to map multiple possible values to a key. Since we just want one value per key, we do not need this type of mapping in the context of an UPDATE. Muzak should handle scenarios where you forget the leading ampersand correctly, but it's best to ensure it is present for proper results.

## Query Syntax

MuzakQL expects you to provide SQL-like query strings with a few notable differences.

1. There is only one 'table', so there is no FROM context. All `select` commands are run on the entire music library
2. Lists of labels to pull should be in parenthesis or brackets ([] or ())
3. The WHERE target needs to be wrapped in curly braces, and preceeded by an ampersand (&) if you want the condition to operate like a SQL AND. Without the ampersand token, the query will operate like a SQL OR.

## Query Output

```
Muzak interactive query prompt
Muzak version 0.8.3

MuzakQL> select [artist, album, title] where {genre=Punk} limit 10
+-----------------------+--------------------------------+------------------+
| artist                | album                          | title            |
+=======================+================================+==================+
| Against All Authority | 24 Hour Roadside Resistance    | I'm Weak Inside  |
+-----------------------+--------------------------------+------------------+
| Against All Authority | Nothing New For Trash Like You | Haymarket Square |
+-----------------------+--------------------------------+------------------+
| Bad Religion          | Back To The Known              | Along The Way    |
+-----------------------+--------------------------------+------------------+
| Bad Religion          | Back To The Known              | Bad Religion     |
+-----------------------+--------------------------------+------------------+
| Bad Religion          | Back To The Known              | Frogger          |
+-----------------------+--------------------------------+------------------+
| Bad Religion          | Back To The Known              | New Leaf         |
+-----------------------+--------------------------------+------------------+
| Bad Religion          | Back To The Known              | Yesterday        |
+-----------------------+--------------------------------+------------------+
| Bad Religion          | Bad Religion                   | Bad Religion     |
+-----------------------+--------------------------------+------------------+
| Bad Religion          | Bad Religion                   | Drastic Actions  |
+-----------------------+--------------------------------+------------------+
| Bad Religion          | Bad Religion                   | Politics         |
+-----------------------+--------------------------------+------------------+
10 records returned
0 records changed
Query executed in 0.001 seconds

MuzakQL>
```
