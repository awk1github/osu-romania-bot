FROM python:3.14.3

# Set the working directory
WORKDIR /app

# Copy the requirements file first (better for caching)
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your friend's code
COPY . .

# Start the bot
CMD ["python", "main.py"]
