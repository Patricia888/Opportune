import requests
import bs4
from bs4 import BeautifulSoup
import urllib3
import pandas as pd
from pyramid.view import view_config
from ..models import Account
from ..models import Keyword
from ..models import Association


@view_config(route_name='search/results', renderer='../templates/email.jinja2')
def get_jobs(request):
    if request.method == 'POST':

        try:
            query = request.dbsession.query(Keyword)
            keyword_query = query.filter(Association.user_id == request.authenticated_userid, Association.keyword_id == Keyword.keyword).all()
            keywords = [keyword.keyword for keyword in keyword_query]
        except DBAPIError:
            raise DBAPIError(DB_ERR_MSG, content_type='text/plain', status=500)

        try:
            city = request.POST['city']
        except KeyError:
            return HTTPBadRequest()

        url_template = 'https://www.indeed.com/jobs?q={}&l={}'
        max_results = 30

        df = pd.DataFrame(columns=['location', 'company', 'job_title', 'salary', 'job_link'])
        requests.packages.urllib3.disable_warnings()
        for keyword in keywords:
            for start in range(0, max_results):
                url = url_template.format(keyword, city)
                http = urllib3.PoolManager()
                response = http.request('GET', url)
                soups = BeautifulSoup(response.data.decode('utf-8'), 'html5lib')
                for b in soups.find_all('div', attrs={'class': ' row result'}):
                    location = b.find('span', attrs={'class': 'location'}).text
                    job_title = b.find('a', attrs={'data-tn-element': 'jobTitle'}).text
                    base_url = 'http://www.indeed.com'
                    href = b.find('a').get('href')
                    job_link = f'{base_url}{href}'
                    try:
                        company = b.find('span', attrs={'class': 'company'}).text
                    except:
                        company = 'Not Listed'
                    try:
                        salary = b.find('span', attrs={'class': 'no-wrap'}).text
                    except:
                        salary = 'Not Listed'
                    df = df.append({'location': location, 'company': company, 'job_title': job_title, 'salary': salary, 'job_link': job_link}, ignore_index=True)

        df.company.replace(regex=True,inplace=True,to_replace='\n',value='')
        df.salary.replace(regex=True,inplace=True,to_replace='\n',value='')
        output = df.head(30)
        output.to_csv('results.csv', index=False)
        return {}