class LocalAiManager < Formula
  desc "Extensible local AI management system with automatic GGUF discovery"
  homepage "https://github.com/user/local-ai-manager"
  url "https://github.com/user/local-ai-manager/archive/v2.0.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"

  depends_on "python@3.12"
  depends_on "llama.cpp" => :optional

  resource "pydantic" do
    url "https://files.pythonhosted.org/packages/.../pydantic-2.0.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "typer" do
    url "https://files.pythonhosted.org/packages/.../typer-0.9.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/.../rich-13.0.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "httpx" do
    url "https://files.pythonhosted.org/packages/.../httpx-0.24.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "psutil" do
    url "https://files.pythonhosted.org/packages/.../psutil-5.9.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "watchdog" do
    url "https://files.pythonhosted.org/packages/.../watchdog-3.0.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  def install
    # Create virtual environment
    venv = virtualenv_create(libexec, "python3.12")
    
    # Install dependencies
    resources.each do |r|
      venv.pip_install r
    end
    
    # Install the package
    venv.pip_install_and_link buildpath
    
    # Create wrapper scripts
    bin.install_symlink libexec/"bin"/"local-ai"
    
    # Create launchd plist for autostart
    (prefix/"local-ai.plist").write <<~EOS
      <?xml version="1.0" encoding="UTF-8"?>
      <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
      <plist version="1.0">
      <dict>
        <key>Label</key>
        <string>#{plist_name}</string>
        <key>ProgramArguments</key>
        <array>
          <string>#{opt_bin}/local-ai</string>
          <string>start</string>
          <string>--background</string>
        </array>
        <key>RunAtLoad</key>
        <true/>
        <key>KeepAlive</key>
        <true/>
      </dict>
      </plist>
    EOS
  end

  def post_install
    # Initialize default config
    system "#{bin}/local-ai", "config-init"
  end

  def caveats
    <<~EOS
      Local AI Manager has been installed!
      
      Quick start:
        local-ai --help
        local-ai start --background
        local-ai status
      
      Configuration:
        ~/.config/local-ai/local-ai-config.json
      
      To enable autostart on login:
        local-ai autostart enable
        
      Or use Homebrew services:
        brew services start local-ai-manager
    EOS
  end

  service do
    run [opt_bin/"local-ai", "start", "--background"]
    keep_alive true
    log_path var/"log/local-ai.log"
    error_log_path var/"log/local-ai.error.log"
  end

  test do
    system "#{bin}/local-ai", "--help"
  end
end
