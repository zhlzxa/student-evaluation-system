#!/bin/bash

# Certificate renewal script for Student Admission Review System

echo "Renewing SSL certificate..."

# Try to renew certificate
if sudo certbot renew --quiet; then
    echo "Certificate renewed successfully"

    # Restart nginx to use new certificate
    echo "Restarting nginx..."
    docker-compose restart nginx

    echo "Certificate renewal completed!"
else
    echo "Certificate renewal failed or not needed"
fi

# Check certificate expiry
echo "Certificate expiry information:"
sudo certbot certificates