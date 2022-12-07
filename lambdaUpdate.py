import argparse
from zipfile import ZipFile
import boto3
import io
import json

def main():
    parser = argparse.ArgumentParser(description='Update Lambda function')
    parser.add_argument('-fn', help='Function name', required=True)
    parser.add_argument('-files',help='List of files to combine into a package',nargs='+', required=True)
    args = parser.parse_args()

    obj = io.BytesIO()
    with ZipFile(obj, 'w') as zip_object:
        row = 0
        for f in args.files:
            # Adding files that need to be zipped
            print(f" - Zipping -- {f}")
            if row == 0:
                filename = 'index.py'
            else:
                filename = f
            
            zip_object.write(f,filename)
            row += 1
    
    # -- update the lambda function's code
    response = boto3.client('lambda').update_function_code(
        FunctionName=args.fn,
        ZipFile=obj.getvalue(),
        Publish=True
    )
    print(json.dumps(response,indent=4))

if __name__ == '__main__':
    main()



