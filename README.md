# analyze-aws-usage-localstack
Analyze your AWS usage with LocalStack and Tinybird


## Developing the LocalStack extensions

### Getting started with extension developer mode

Prerequisites:

* Install the LocalStack CLI and cookiecutter for templating `pip install --upgrade localstack cookiecutter`
* Log in to your LocalStack Pro account with `localstack login`

Create a new extension and follow the template wizard

```console
 % localstack extensions dev new

You've downloaded /home/thomas/.cookiecutters/localstack-extensions before. Is it okay to delete and re-download it? [yes]: yes
project_name [My LocalStack Extension]: LocalStack Tinybird Logger    
project_short_description [All the boilerplate you need to create a LocalStack extension.]: LocalStack extension to log AWS API calls into Tinybird
project_slug [localstack-tinybird-logger]: 
module_name [localstack_tinybird_logger]: 
full_name [Jane Doe]: Thomas Rausch      
email [jane@example.com]: thomas@localstack.cloud
github_username [janedoe]: thrau
version [0.1.0]: 
```

Enable dev mode for the new extension
```console
 % localstack extensions dev enable localstack-tinybird-logger
/home/thomas/workspace/localstack/analyze-aws-usage-localstack/localstack-tinybird-logger enabled
```

Package the extension so it can be loaded by localstack
```console
 % cd localstack-tinybird-logger && make install
```
This will create a virtual environment containing all the dependencies required to load the extension.
LocalStack comes with a lot of transitive dependencies, including `requests`, which you can simply use out of the box, but it's advisable to add dependencies explicitly as the project matures.
When you extend the `setup.cfg`, run `make install` again.

Start LocalStack with extension dev mode enabled:
```console
 % LOCALSTACK_API_KEY=********** EXTENSION_DEV_MODE=1 localstack start
```
You should see `MyExtension: localstack is running` in the log. If so, you are ready to develop the extension!

### Basic idea of the extension

We want to record every AWS API call going through LocalStack to Tinybird.
To that end, we can extend the *response handlers* of the LocalStack Gateway, which is the component responsible for parsing and dispatching an AWS API call to the corresponding backend.
With a custom response handler, you can intercept all API calls after they have been processed by the backend, and run custom logic.
You can [find out more about how the LocalStack Gateway works](https://localstack.notion.site/LocalStack-Core-Concepts-cd342b31882946a0a3dfb4a7b21e8792#ccbea13c299d4b90b5e12d04c7add1b4) in our contributing guide.


### Intercepting the request

Conceptually, we want to intercept the AWS request and the generated response with a service response handler, create a log record, and post that log record to Tinybird.
In LocalStack, every AWS request is encapsulated in a `RequestContext` object that goes through several handlers that are part of the `HandlerChain`.
The request context contains which AWS service the request is made to, which API operation, and other metadata.
It also contains the parsed AWS request, i.e., the parameters to the operation, which we can add as an optional payload.

```python
def logger(chain: HandlerChain, context: RequestContext, response: Response):
    payload = {
        "service": context.service.service_name, # e.g., "sqs" or "s3"
        "operation": context.operation.name, # e.g., "CreateQueue" or "DeleteBucket"
        "request": json.dumps(context.service_request), # the request parameters
        "status_code": response.status_code, # the HTTP status code the backend created
        "response": json.dumps(context.service_response), # the response from the service backend
        # ... additional metadata can be added
    }

```

### Send the request to Tinybird

For our logger, all we need to do is create a JSON document from our payload and make a POST request to the Tinybird events HFI endpoint.
This is as easy as:

```python
def logger(...):
    # ...
    event = json.dumps(payload)

    requests.post(
        url="https://api.tinybird.co/v0/events?name=aws_api_calls",
        data=event,
        headers={
            "Authorization": "Bearer <tinybird token>"
        }
    )
```

## Tinybird analytics

... TODO

### Getting started with queries

Here are some example queries to run:

The number of localstack runs per day:

```sql
SELECT
  toDate(`timestamp`) as `date`,
  countDistinct(session_id) as number_of_sessions
FROM aws_api_calls
GROUP BY `date`
```

The most used service operation:

```sql
SELECT
  service,
  operation,
  countDistinct(session_id) as number_of_sessions
FROM aws_api_calls
GROUP BY service, operation
```

De-normalize specific AWS operations:

```sql
SELECT
  timestamp,
  operation,
  JSONExtractString(request, 'Bucket') as bucket
FROM aws_api_calls
WHERE service == 's3'
```

### Materialization

... TODO
