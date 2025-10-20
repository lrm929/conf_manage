# 配置文件生成系统

一个现代化的配置文件生成和管理系统，支持多项目配置管理、模板文件上传、一键生成和下载配置文件。

## 功能特点

### 🚀 核心功能
- **项目管理**: 创建、编辑、删除项目，每个项目支持独立的配置文件
- **模板管理**: 上传和管理配置文件模板，支持多种格式（XML、JSON、ENV等）
- **配置生成**: 基于模板和自定义参数一键生成配置文件
- **文件下载**: 自动打包生成的配置文件并提供下载

### 🔐 安全特性
- **用户认证**: 基于Session的用户登录系统
- **权限管理**: 支持用户角色管理
- **数据安全**: SQLite数据库存储，数据持久化

### 🎨 界面设计
- **现代化UI**: 简洁大方的界面设计
- **响应式布局**: 支持桌面和移动设备
- **交互体验**: 拖拽上传、实时预览、动画效果

## 技术架构

### 后端技术
- **Python 3.7+**: 主要开发语言
- **Flask**: Web框架
- **SQLite**: 数据库
- **Flask-CORS**: 跨域支持

### 前端技术
- **HTML5**: 页面结构
- **CSS3**: 样式设计（渐变、动画、响应式）
- **JavaScript**: 交互逻辑
- **Font Awesome**: 图标库

## 安装和运行

### 环境要求
- Python 3.8 或更高版本
- pip 包管理器
- Linux系统 (推荐Ubuntu 18.04+, CentOS 7+)

### 快速启动 (Linux)

1. **下载项目**
   ```bash
   git clone <repository-url>
   cd config-generator-system
   ```

2. **启动服务**
   ```bash
   # 给脚本执行权限
   chmod +x manage.sh
   
   # 启动服务
   ./manage.sh start
   ```

3. **访问系统**
   打开浏览器访问: `http://localhost:5000`


### 服务管理

使用统一的管理脚本进行服务管理：

```bash
# 基本服务管理
./manage.sh start      # 启动服务
./manage.sh stop       # 停止服务
./manage.sh restart    # 重启服务
./manage.sh status     # 查看状态
./manage.sh logs       # 查看日志

# 系统服务管理 (需要root权限)
sudo ./manage.sh install    # 安装为系统服务
sudo ./manage.sh uninstall  # 卸载系统服务

# 安装为系统服务后，可使用systemctl管理
sudo systemctl start config-generator    # 启动服务
sudo systemctl stop config-generator     # 停止服务
sudo systemctl restart config-generator  # 重启服务
sudo systemctl status config-generator   # 查看状态
sudo systemctl enable config-generator  # 开机自启
sudo systemctl disable config-generator # 禁用自启

# 查看系统服务日志
sudo journalctl -u config-generator -f
```

### 默认登录信息
- 用户名: `admin`
- 密码: `admin123`

## 使用指南

### 1. 项目管理
1. 登录系统后，点击"项目管理"标签
2. 填写项目信息（名称、描述、模板路径）
3. 点击"创建项目"按钮
4. 在项目列表中管理现有项目

### 2. 模板管理
1. 切换到"模板管理"标签
2. 拖拽文件到上传区域或点击选择文件
3. 支持多种格式：`.config`, `.json`, `.env`, `.xml`等
4. 在模板列表中查看已上传的文件

### 3. 配置生成
1. 切换到"配置生成"标签
2. 选择要生成配置的项目
3. 填写配置参数（应用名称、版本、数据库地址等）
4. 点击"生成并下载"按钮
5. 系统会自动生成配置文件并打包下载

## 模板语法

系统支持模板变量替换，使用双大括号语法：

```
{{variable_name}}
```

### 示例模板
```xml
<configuration>
  <appSettings>
    <add key="AppName" value="{{app_name}}" />
    <add key="Version" value="{{app_version}}" />
  </appSettings>
</configuration>
```

### 支持的变量类型
- `app_name`: 应用名称
- `app_version`: 应用版本
- `database_url`: 数据库连接地址
- `debug_mode`: 调试模式
- `log_level`: 日志级别
- 自定义变量...

## 项目结构

```
config-generator-system/
├── backend/                 # 后端代码
│   ├── app.py              # Flask应用主文件
│   └── templates/          # Flask模板
├── frontend/               # 前端代码
│   └── index.html          # 主页面
├── templates/              # 配置文件模板
│   ├── web.config          # ASP.NET配置模板
│   ├── app.env             # 环境变量模板
│   └── config.json         # JSON配置模板
├── uploads/                # 上传文件目录
├── downloads/              # 下载文件目录
├── requirements.txt        # Python依赖
├── manage.sh              # 统一服务管理脚本
├── Dockerfile             # Docker镜像配置
├── docker-compose.yml     # Docker Compose配置
└── README.md              # 项目文档
```

## API接口

### 认证接口
- `POST /login` - 用户登录
- `POST /logout` - 用户登出

### 项目管理
- `GET /api/projects` - 获取项目列表
- `POST /api/projects` - 创建项目
- `PUT /api/projects/<id>` - 更新项目
- `DELETE /api/projects/<id>` - 删除项目

### 模板管理
- `GET /api/templates` - 获取模板列表
- `POST /api/templates/upload` - 上传模板文件

### 配置生成
- `POST /api/projects/<id>/generate` - 生成配置文件
- `GET /api/download/<filename>` - 下载文件

## 数据库结构

### users 表
- `id`: 用户ID（主键）
- `username`: 用户名
- `password_hash`: 密码哈希
- `email`: 邮箱
- `role`: 用户角色
- `created_at`: 创建时间

### projects 表
- `id`: 项目ID（主键）
- `name`: 项目名称
- `description`: 项目描述
- `template_path`: 模板路径
- `config_data`: 配置数据（JSON）
- `user_id`: 用户ID（外键）
- `created_at`: 创建时间
- `updated_at`: 更新时间

### config_files 表
- `id`: 文件ID（主键）
- `project_id`: 项目ID（外键）
- `file_name`: 文件名
- `file_path`: 文件路径
- `template_content`: 模板内容
- `generated_content`: 生成内容
- `created_at`: 创建时间

## 开发说明

### 添加新的模板类型
1. 在`templates/`目录下添加新的模板文件
2. 使用`{{variable_name}}`语法定义变量
3. 在配置生成时提供对应的变量值

### 扩展配置参数
1. 修改前端`generateConfigForm()`函数
2. 添加新的配置项到表单
3. 后端会自动处理新的配置参数

### 自定义样式
1. 修改`frontend/index.html`中的CSS样式
2. 支持响应式设计和主题定制
3. 使用CSS变量便于主题切换

## 故障排除

### 常见问题

1. **端口占用**
   - 修改`app.py`中的端口号
   - 检查5000端口是否被占用

2. **文件上传失败**
   - 检查`uploads/`目录权限
   - 确认文件大小限制

3. **数据库错误**
   - 删除`config_system.db`重新初始化
   - 检查SQLite版本兼容性

4. **模板解析错误**
   - 检查模板文件语法
   - 确认变量名格式正确

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。


