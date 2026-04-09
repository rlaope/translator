export async function readStdin() {
  return new Promise((resolve, reject) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', chunk => { data += chunk; });
    process.stdin.on('end', () => {
      try {
        resolve(JSON.parse(data));
      } catch (e) {
        reject(new Error(`Failed to parse stdin: ${e.message}`));
      }
    });
    process.stdin.on('error', reject);
    // Timeout safety - if no data after 2s, resolve empty
    setTimeout(() => {
      if (!data) resolve({});
    }, 2000);
  });
}
