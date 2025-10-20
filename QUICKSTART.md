# 配置文件生成系统 - 快速使用指南

## 快速启动

1. **给脚本执行权限**
   ```bash
   chmod +x manage.sh
   ```

2. **启动服务**
   ```bash
   ./manage.sh start
   ```

3. **访问系统**
   打开浏览器访问: http://localhost:5000
   默认登录: admin / admin123

## 服务管理命令

```bash
./manage.sh start      # 启动服务
./manage.sh stop       # 停止服务
./manage.sh restart    # 重启服务
./manage.sh status     # 查看状态
./manage.sh logs       # 查看日志
./manage.sh help       # 显示帮助
```

## 系统服务管理

如果需要开机自启，可以安装为系统服务：

```bash
# 安装为系统服务 (需要root权限)
sudo ./manage.sh install

# 安装后可使用systemctl管理
sudo systemctl start config-generator
sudo systemctl stop config-generator
sudo systemctl enable config-generator  # 开机自启
```

## 功能说明

1. **项目管理**: 创建、编辑、删除项目
2. **模板管理**: 上传配置文件模板
3. **配置生成**: 基于模板生成配置文件并下载

## 故障排除

如果启动失败，请检查：
1. Python3是否已安装
2. pip3是否可用
3. 端口5000是否被占用
4. 查看日志: `./manage.sh logs`
