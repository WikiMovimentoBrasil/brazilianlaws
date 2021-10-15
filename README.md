<img src="https://img.shields.io/github/issues/WikiMovimentoBrasil/brazilianlaws?style=for-the-badge"/> <img src="https://img.shields.io/github/license/WikiMovimentoBrasil/brazilianlaws?style=for-the-badge"/> <img src="https://img.shields.io/github/languages/top/WikiMovimentoBrasil/brazilianlaws?style=for-the-badge"/>
# Brazilian Laws

This tool is a metadata application to be hosted in Toolforge. It invites Wikimedia users to create a Wikidata item of a law contained in the LexML database. 

The tool presents a text field where the URL to a LexML law can be added. Once the law has been parsed by the tool, the users see a list of metada to be reconciled. Items reconciled automatically are listed in gree, while those in need of being manually reviewed by the user are displayed in red. 

This tool is available live at: http://brazilianlaws.toolforge.org

More information on the WikiProject Brazilian Laws can be found at: https://www.wikidata.org/wiki/Wikidata:WikiProject_Brazilian_Laws

## Installation

There are several packages need to this application to function. All of them are listed in the <code>requeriments.txt</code> file. To install them, use

```bash
pip install -r requirements.txt
```

You also need to set the configuration file. To do this, you need [a Oauth consumer token and Oauth consumer secret](https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration/propose).
Your config file should look like this:
```bash
SECRET_KEY: "YOUR_SECRET_KEY"
BABEL_DEFAULT_LOCALE: "pt"
APPLICATION_ROOT: "brazilianlaws/"
OAUTH_MWURI: "https://meta.wikimedia.org/w/index.php"
CONSUMER_KEY: "YOUR_CONSUMER_KEY"
CONSUMER_SECRET: "YOUR_CONSUMER_SECRET"
LANGUAGES: ["pt","en"]
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
[GNU General Public License v3.0](https://github.com/WikiMovimentoBrasil/wikimotivos/blob/master/LICENSE)

## Credits
This application was developed in the context of the Novo Museu do Ipiranga Project, organized by the Wiki Movimento Brasil User Group and the Museu