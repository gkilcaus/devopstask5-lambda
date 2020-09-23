### devopstask5-lambda

- lambda_function.py - python based lambda function for scheduling EC2 shutdown/startup
  - requirements.txt - python dependencies for lambda
- template.yaml - AWS SAM template to build function and related IAM Role
- buildspec.yml - CodeBuild template to provision/update function using AWS SAM

# Manual deployment of SAM template
```bash
sam build
sam package --s3-bucket <s3_bucket> --s3-prefix sampkg-code --output-template-file packaged.yaml
sam deploy --template-file packaged.yaml --stack-name <stack_name> --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM
```
# destroy
```bash
aws cloudformation delete-stack --stack-name <stack_name>
```