rm -rf ./dist
python setup.py bdist_wheel --universal
twine upload dist/*

