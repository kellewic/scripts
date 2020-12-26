#!/bin/bash

OPENSSL="$(which openssl)"
HOST=$1

if [ -z "$HOST" ]; then
    echo "HOST MUST BE SPECIFIED!"
    exit 1
fi

PRIVATE_KEY_FILE="${HOST}-priv.pem"
PASSWORD_FILE="${HOST}.pwd"
CSR_FILE="${HOST}.csr"

## Used for subject of cert
C="US"
ST="Arizona"
L="Phoenix"
O="My Org"
OU="My Team"

## Generate password for key
echo -n "$(LC_ALL=C tr -dc 'A-Za-z0-9!"#$%&'\''()*+,-./:;<=>?@[\]^_`{|}~' </dev/urandom | head -c 16)" > $PASSWORD_FILE 

## Create private key
$OPENSSL genrsa -des3 -out $PRIVATE_KEY_FILE -passout file:$PASSWORD_FILE 2048

## Create CSR using private key
$OPENSSL req -new -passin file:$PASSWORD_FILE -key $PRIVATE_KEY_FILE -out $CSR_FILE -subj "/C=${C}/ST=${ST}/L=${L}/O=${O}/OU=${OU}/CN=${HOST}/"

## Remove password from private key
$OPENSSL rsa -in $PRIVATE_KEY_FILE -out $PRIVATE_KEY_FILE -passin file:$PASSWORD_FILE

