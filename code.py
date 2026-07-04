import pygame
import sys
import os
import math
import random
from enum import Enum, auto

#  常量定义
SCREEN_WIDTH  = 480
SCREEN_HEIGHT = 700
FPS           = 60
TITLE         = "空战游戏"

# 颜色
COLOR_WHITE  = (255, 255, 255)
COLOR_BLACK  = (0,   0,   0  )
COLOR_RED    = (220, 50,  50 )
COLOR_YELLOW = (255, 220, 0  )
COLOR_GREEN  = (50,  200, 80 )
COLOR_CYAN   = (0,   200, 220)
COLOR_GRAY   = (150, 150, 150)
COLOR_ORANGE = (255, 140, 0  )

# 游戏状态
class GameState(Enum):
    START   = auto()
    PLAYING = auto()
    WIN     = auto()
    LOSE    = auto()

# 敌机运动轨迹类型
class MovementType(Enum):
    STRAIGHT = auto()   # 直线下落
    WAVE     = auto()   # 波浪运动
    TRACKING = auto()   # 追踪玩家


#  资源管理器：统一加载并缓存游戏所需的所有图片资源。
class ResourceManager:
    def __init__(self, resourceDir: str = "images"):
        self.imageCache: dict  = {}
        self.resourceDir: str  = resourceDir

    def loadImage(self, fileName: str, size: tuple = None) -> pygame.Surface:
        """
        加载图片，缩放图片
        args:
            fileName: 图片文件名
            size:  代表缩放尺寸 None 表示不缩放。
        return:
            pygame.Surface: 加载的图片Surface
        """
        filePath = os.path.join(self.resourceDir, fileName)
        cacheKey = f"{filePath}_{size}"

        if cacheKey in self.imageCache:
            return self.imageCache[cacheKey]

        surface = pygame.image.load(filePath).convert_alpha()
        if size:
            surface = pygame.transform.scale(surface, size)

        self.imageCache[cacheKey] = surface
        return surface

    def loadBackgrounds(self, count= 7) :
        """
        加载多张背景图。
        args:
            count: 背景图总数量。
        return:
            list: 背景图列表。
        """
        backgrounds = []
        bgNames = [
            "background_01.png", "background_02.png", "background_03.png",
            "background_04.png", "background_05.png", "background_06.png",
            "background_07.png",
        ]
        for i in range(count):
            name = bgNames[i] if i < len(bgNames) else f"background_{i+1:02d}.png"
            bg   = self.loadImage(name, (SCREEN_WIDTH, SCREEN_HEIGHT))
            backgrounds.append(bg)
        return backgrounds

    def loadEnemyFrames(self, groupIndex):
        """
        加载敌机动画。
        args:
            groupIndex: 敌机组编号
        return:
            list:动画图片列表。
        """
        frames = []
        for frameIndex in range(1, 5):
            name    = f"enemyPlane_0{groupIndex}_0{frameIndex}.png"
            surface = self.loadImage(name, (60, 60))
            frames.append(surface)
        return frames

    

#  子弹基类
class Bullet(pygame.sprite.Sprite):
    def __init__(self, image: pygame.Surface, x, y,
                 speedX, speedY, damage= 1):
        super().__init__()
        self.image  = image
        self.rect   = self.image.get_rect(center=(x, y))
        self.speedX = speedX
        self.speedY = speedY
        self.damage = damage

    def update(self):
        #每帧更新子弹位置，飞出屏幕后自动销毁。
        self.rect.x += self.speedX
        self.rect.y += self.speedY
        if (self.rect.bottom < 0 or self.rect.top > SCREEN_HEIGHT
                or self.rect.right < 0 or self.rect.left > SCREEN_WIDTH):
            self.kill()
#  玩家子弹
class PlayerBullet(Bullet):
    """
    玩家战机发射的子弹，向上飞行。
    args:
        image: 子弹图片。
        x, y:  初始坐标。
    """
    def __init__(self, image, x, y):
        super().__init__(image, x, y, speedX=0, speedY=-12, damage=1)
#  敌机子弹
class EnemyBullet(Bullet):
    #普通敌机发射的子弹，向下飞行。
    def __init__(self, image, x, y):
        super().__init__(image, x, y, speedX=0, speedY=5, damage=1)
#  BOSS 子弹
class BossBullet(Bullet):
    #BOSS发射的子弹，可沿任意方向飞行。
    def __init__(self, image: pygame.Surface, x: float, y: float,
                 angle: float, speed: float = 4):
        rad    = math.radians(angle)
        speedX = math.cos(rad) * speed
        speedY = math.sin(rad) * speed
        super().__init__(image, x, y, speedX=speedX, speedY=speedY, damage=2)



#  玩家战机
class PlayerPlane(pygame.sprite.Sprite):
    SPEED          = 5
    MAX_HP         = 5
    SHOOT_COOLDOWN = 15       # 帧
    INVINCIBLE_FRAMES = 90    # 受伤后无敌帧数

    def __init__(self, image, bulletImages):
        super().__init__()
        self.image        = image
        self.rect         = self.image.get_rect(
            center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100))
        self.speed        = self.SPEED
        self.maxHp        = self.MAX_HP
        self.hp           = self.MAX_HP
        self.bulletImages = bulletImages
        self.shootCooldown  = self.SHOOT_COOLDOWN
        self.shootTimer     = 0
        self.bulletGroup    = pygame.sprite.Group()
        self.isInvincible   = False
        self.invincibleTimer = 0

    def update(self, keys: pygame.key.ScancodeWrapper):
        self._handleMovement(keys)
        self._handleInvincible()
        self._decreaseCooldown()
        self.bulletGroup.update()

    def _handleMovement(self, keys):
        #根据方向键移动战机
        if keys[pygame.K_LEFT]  and self.rect.left  > 0:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT] and self.rect.right  < SCREEN_WIDTH:
            self.rect.x += self.speed
        if keys[pygame.K_UP]   and self.rect.top    > 0:
            self.rect.y -= self.speed
        if keys[pygame.K_DOWN] and self.rect.bottom < SCREEN_HEIGHT:
            self.rect.y += self.speed

    def _handleInvincible(self):
        #处理无敌帧
        if self.isInvincible:
            self.invincibleTimer -= 1
            if self.invincibleTimer <= 0:
                self.isInvincible = False

    def _decreaseCooldown(self):
        #减少射击冷却计时器
        if self.shootTimer > 0:
            self.shootTimer -= 1

    def shoot(self):
        #玩家按下空格键时调用，在冷却结束后发射子弹。
        #根据子弹图片数量发射单发或三发。
    
        if self.shootTimer > 0:
            return
        self.shootTimer = self.shootCooldown

        cx, cy = self.rect.centerx, self.rect.top + 5
        bulletImg = self.bulletImages[0] if self.bulletImages else None
        if bulletImg is None:
            return

        # 单发主弹
        self.bulletGroup.add(PlayerBullet(bulletImg, cx, cy))

        # 若有第二、三种子弹图片，同时发射侧翼弹
        if len(self.bulletImages) >= 2:
            sideImg = self.bulletImages[1]
            self.bulletGroup.add(PlayerBullet(sideImg, cx - 18, cy + 10))
            self.bulletGroup.add(PlayerBullet(sideImg, cx + 18, cy + 10))

    def takeDamage(self, amount = 1):
        if self.isInvincible:
            return False
        self.hp -= amount
        self.isInvincible = True
        self.invincibleTimer = self.INVINCIBLE_FRAMES
        return self.hp <= 0

    def draw(self, screen):
        # 无敌闪烁：每 6 帧切换一次可见性
        if not self.isInvincible or (self.invincibleTimer // 6) % 2 == 0:
            screen.blit(self.image, self.rect)
        self.bulletGroup.draw(screen)



#  敌机基类
class EnemyPlane(pygame.sprite.Sprite):
    FRAME_INTERVAL = 8    # 动画帧切换间隔
    BASE_HP        = 3
    BASE_SCORE     = 100

    def __init__(self, frames, bulletImage,
                 x, y, shootInterval = 90):
        super().__init__()
        self.frames      = frames
        self.frameIndex  = 0
        self.frameTimer  = 0
        self.image       = frames[0]
        self.rect        = self.image.get_rect(center=(x, y))
        self.hp          = self.BASE_HP
        self.maxHp       = self.BASE_HP
        self.bulletImage = bulletImage
        self.shootInterval = shootInterval
        self.shootTimer    = random.randint(0, shootInterval)
        self.bulletGroup   = pygame.sprite.Group()
        self.score         = self.BASE_SCORE

    def updateAnimation(self):
        #切换动画帧，每隔 FRAME_INTERVAL 帧更换一张
        self.frameTimer += 1
        if self.frameTimer >= self.FRAME_INTERVAL:
            self.frameTimer  = 0
            self.frameIndex  = (self.frameIndex + 1) % len(self.frames)
            self.image       = self.frames[self.frameIndex]

    def tryShoot(self):
        #尝试发射子弹，根据 shootInterval 控制频率。
        self.shootTimer -= 1
        if self.shootTimer <= 0:
            self.shootTimer = self.shootInterval
            self._fireBullet()

    def _fireBullet(self):
        """
        发射一枚向下飞行的子弹。
        子类可重写此方法以实现不同弹道。
        """
        bullet = EnemyBullet(self.bulletImage,
                             self.rect.centerx,
                             self.rect.bottom)
        self.bulletGroup.add(bullet)

    def takeDamage(self, amount = 1):
        self.hp -= amount
        return self.hp <= 0

    def update(self, playerRect = None):
        """
        更新敌机状态
        子类需调用 super().update() 并实现 move()。
        args:
            playerRect: 玩家战机的 Rect，用于追踪型敌机。
        """
        self.updateAnimation()
        self._move(playerRect)
        self.tryShoot()
        self.bulletGroup.update()

        # 飞出屏幕底部时销毁
        if self.rect.top > SCREEN_HEIGHT + 50:
            self.kill()

    def _move(self, playerRect = None):
        raise NotImplementedError

    def draw(self, screen):
        #绘制敌机、血条和子弹。
        screen.blit(self.image, self.rect)
        self._drawHpBar(screen)
        self.bulletGroup.draw(screen)

    def _drawHpBar(self, screen):
        #在敌机上方绘制血量条
        barWidth  = self.rect.width
        barHeight = 4
        barX      = self.rect.left
        barY      = self.rect.top - 7
        ratio     = max(0, self.hp / self.maxHp)

        pygame.draw.rect(screen, COLOR_GRAY,  (barX, barY, barWidth, barHeight))
        pygame.draw.rect(screen, COLOR_GREEN, (barX, barY, int(barWidth * ratio), barHeight))
#  直线运动敌机
class StraightEnemy(EnemyPlane):
    def __init__(self, frames, bulletImage, x):
        super().__init__(frames, bulletImage, x, -40)
        self.speedY = random.uniform(2.0, 3.5)

    def _move(self, playerRect=None):
        #直线下移
        self.rect.y += self.speedY
#  波浪运动敌机
class WaveEnemy(EnemyPlane):
    def __init__(self, frames, bulletImage, x):
        super().__init__(frames, bulletImage, x, -40)
        self.speedY        = random.uniform(1.5, 2.5)
        self.waveAmplitude = random.uniform(40, 80)
        self.waveFrequency = random.uniform(0.04, 0.08)
        self.wavePhase     = random.uniform(0, math.pi * 2)
        self.originX       = float(x)

    def _move(self, playerRect=None):
        #正弦波浪横向摆动，同时向下移动
        self.rect.y   += self.speedY
        self.wavePhase += self.waveFrequency
        self.rect.centerx = int(self.originX + math.sin(self.wavePhase) * self.waveAmplitude)
        # 限制在屏幕内
        self.rect.centerx = max(self.rect.width  // 2,
                                min(SCREEN_WIDTH - self.rect.width // 2,
                                    self.rect.centerx))
#  追踪运动敌机
class TrackingEnemy(EnemyPlane):
    def __init__(self, frames, bulletImage, x):
        super().__init__(frames, bulletImage, x, -40, shootInterval=70)
        self.speedY         = random.uniform(1.2, 2.0)
        self.speedX         = random.uniform(1.5, 2.5)
        self.trackingStartY = random.randint(80, 180)

    def _move(self, playerRect = None):
        #先垂直下落至 trackingStartY，之后水平追踪玩家 X 坐标。
        self.rect.y += self.speedY
        if playerRect and self.rect.top > self.trackingStartY:
            if self.rect.centerx < playerRect.centerx:
                self.rect.x += self.speedX
            elif self.rect.centerx > playerRect.centerx:
                self.rect.x -= self.speedX


#  BOSS
class Boss(pygame.sprite.Sprite):
    MAX_HP         = 30# 最大血量
    SHOOT_INTERVAL = 80# 射击间隔
    SCORE          = 2000# 击毁得分
    SPEED_X        = 2.5# 水平速度

    def __init__(self, image, bulletImage):
        super().__init__()
        self.image         = pygame.transform.scale(image, (120, 100))
        self.rect          = self.image.get_rect(center=(SCREEN_WIDTH // 2, 80))
        self.hp            = self.MAX_HP
        self.maxHp         = self.MAX_HP
        self.bulletImage   = bulletImage
        self.bulletGroup   = pygame.sprite.Group()
        self.speedX        = self.SPEED_X
        self.shootTimer    = 0
        self.shootInterval = self.SHOOT_INTERVAL
        self.score         = self.SCORE
        self.phase         = 1

    def update(self):
        #更新 BOSS 位置、阶段状态、子弹
        self._moveHorizontally()
        self._updatePhase()
        self._tryShoot()
        self.bulletGroup.update()

    def _moveHorizontally(self):
        #左右匀速往返摆动。
        self.rect.x += self.speedX
        if self.rect.right >= SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
            self.speedX = -abs(self.speedX)
        elif self.rect.left <= 0:
            self.rect.left = 0
            self.speedX = abs(self.speedX)
    def _updatePhase(self):
        #血量低于 50% 时进入第二阶段，射击更频繁。
        if self.hp <= self.maxHp // 2 and self.phase == 1:
            self.phase         = 2
            self.shootInterval = 50

    def _tryShoot(self):
        self.shootTimer += 1
        if self.shootTimer >= self.shootInterval:
            self.shootTimer = 0
            self._fireSpread()

    def _fireSpread(self):
        bulletCount = 8 if self.phase == 1 else 12
        for i in range(bulletCount):
            angle  = (360 / bulletCount) * i + 90   # 从正下方开始均匀分布
            bullet = BossBullet(self.bulletImage,
                                self.rect.centerx,
                                self.rect.bottom,
                                angle, speed=4.5)
            self.bulletGroup.add(bullet)

    def takeDamage(self, amount = 1) -> bool:
        self.hp -= amount
        return self.hp <= 0

    def draw(self, screen):
        #绘制 BOSS 本体、血条和子弹
        screen.blit(self.image, self.rect)
        self._drawHpBar(screen)
        self.bulletGroup.draw(screen)

    def _drawHpBar(self, screen):
        #在屏幕顶部绘制宽幅 BOSS 血条。
        barWidth  = SCREEN_WIDTH - 40
        barHeight = 12
        barX      = 20
        barY      = 8
        ratio     = max(0, self.hp / self.maxHp)

        pygame.draw.rect(screen, COLOR_GRAY, (barX, barY, barWidth, barHeight))
        pygame.draw.rect(screen, COLOR_RED,  (barX, barY, int(barWidth * ratio), barHeight))
        pygame.draw.rect(screen, COLOR_WHITE,(barX, barY, barWidth, barHeight), 1)

        font  = pygame.font.SysFont("microsoftyahei", 10)
        label = font.render("BOSS HP", True, COLOR_WHITE)
        screen.blit(label, (barX + 4, barY - 1))



#  背景滚动器
class BackgroundScroller:
    SCROLL_SPEED    = 2.0#滚动速度
    SWITCH_INTERVAL = 600   #背景图切换间隔

    def __init__(self, images):
        self.images        = images
        self.currentIndex  = 0  #当前背景图索引。
        self.y1            = 0.0
        self.y2            = float(-SCREEN_HEIGHT)
        self.scrollSpeed   = self.SCROLL_SPEED
        self.switchInterval = self.SWITCH_INTERVAL
        self.switchTimer    = 0

    def update(self):
        #向下滚动背景，滚出屏幕时循环；定时切换背景图。
        self.y1 += self.scrollSpeed
        self.y2 += self.scrollSpeed

        if self.y1 >= SCREEN_HEIGHT:
            self.y1 = self.y2 - SCREEN_HEIGHT
        if self.y2 >= SCREEN_HEIGHT:
            self.y2 = self.y1 - SCREEN_HEIGHT

        self.switchTimer += 1
        if self.switchTimer >= self.switchInterval:
            self.switchTimer  = 0
            self.currentIndex = (self.currentIndex + 1) % len(self.images)

    def draw(self, screen):
        bg = self.images[self.currentIndex]
        screen.blit(bg, (0, int(self.y1)))
        screen.blit(bg, (0, int(self.y2)))


#  敌机生成器
class EnemySpawner:
    SPAWN_INTERVAL = 80   # 每隔约 1.3 秒生成一架

    def __init__(self, enemyGroups: list, bulletImages: list, totalEnemies: int = 12):
        self.enemyGroups   = enemyGroups  #三组敌机帧列表。
        self.bulletImages  = bulletImages #四张子弹图片列表
        self.totalToSpawn  = totalEnemies  #计划生成的敌机总数。
        self.spawnedCount  = 0# 已生成的数量
        self.spawnTimer    = 0# 生成计时器
        self.spawnInterval = self.SPAWN_INTERVAL#生成间隔
        self.finished      = False
        self.spawnQueue    = self._buildSpawnQueue(totalEnemies)

    def _buildSpawnQueue(self, total):
        #构建随机排列的敌机生成队列，确保三种轨迹都出现。
        types    = [MovementType.STRAIGHT, MovementType.WAVE, MovementType.TRACKING]
        groups   = [0, 1, 2]  # 敌机图片组索引

        queue = []
        # 保证每种轨迹至少出现一次
        for mType in types:
            queue.append((mType, random.choice(groups)))

        # 剩余随机填充
        while len(queue) < total:
            queue.append((random.choice(types), random.choice(groups)))

        random.shuffle(queue)
        return queue

    def update(self, enemyGroup):
        if self.finished:
            return

        self.spawnTimer += 1
        if self.spawnTimer < self.spawnInterval:
            return

        self.spawnTimer = 0
        if not self.spawnQueue:
            self.finished = True
            return

        movementType, groupIdx = self.spawnQueue.pop(0)
        self.spawnedCount += 1

        x         = random.randint(40, SCREEN_WIDTH - 40)
        frames    = self.enemyGroups[groupIdx]
        bulletImg = random.choice(self.bulletImages)

        enemy = self._createEnemy(movementType, frames, bulletImg, x)
        enemyGroup.add(enemy)

        if not self.spawnQueue:
            self.finished = True

    def _createEnemy(self, movementType,frames, bulletImg,x):
        """
        根据运动类型实例化对应的敌机对象。
        agrs:
            movementType:运动轨迹类型。
            frames:动画帧列表。
            bulletImg:子弹图片。
            x:初始 X 坐标。
        """
        if movementType == MovementType.STRAIGHT:
            return StraightEnemy(frames, bulletImg, x)
        elif movementType == MovementType.WAVE:
            return WaveEnemy(frames, bulletImg, x)
        else:
            return TrackingEnemy(frames, bulletImg, x)



#  HUD（抬头显示）
class HUD:
    def __init__(self):
        self.fontLarge = pygame.font.SysFont("microsoftyahei", 22, bold=True)#分数字体
        self.fontSmall = pygame.font.SysFont("microsoftyahei", 16)#标签字体

    def draw(self, screen, score, hp, maxHp, enemyLeft):
        # 半透明底栏
        barSurface = pygame.Surface((SCREEN_WIDTH, 40), pygame.SRCALPHA)
        barSurface.fill((0, 0, 0, 130))
        screen.blit(barSurface, (0, SCREEN_HEIGHT - 40))

        # 分数
        scoreText = self.fontLarge.render(f"分数: {score}", True, COLOR_YELLOW)
        screen.blit(scoreText, (10, SCREEN_HEIGHT - 35))

        # 生命值
        # 绘制生命值方块（红色=有血，灰色=已损失）
        blockSize = 18
        blockGap  = 6
        totalWidth = maxHp * (blockSize + blockGap)
        startX = SCREEN_WIDTH // 2 - totalWidth // 2
        startY = SCREEN_HEIGHT - 32
        for i in range(maxHp):
            color = COLOR_RED if i < hp else COLOR_GRAY
            pygame.draw.rect(screen, color,
                             (startX + i * (blockSize + blockGap),
                              startY, blockSize, blockSize))

        # 剩余敌机
        enemyText = self.fontSmall.render(f"敌机: {enemyLeft}", True, COLOR_CYAN)
        screen.blit(enemyText, (SCREEN_WIDTH - enemyText.get_width() - 10,
                                SCREEN_HEIGHT - 32))


#  爆炸效果
class Explosion(pygame.sprite.Sprite):
    LIFESPAN = 30 #爆炸时长

    def __init__(self, x, y):
        super().__init__()
        self.image    = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.rect     = self.image.get_rect(center=(x, y))
        self.lifespan = self.LIFESPAN
        self.timer    = 0
        self.particles = self._createParticles(x, y)

    def _createParticles(self, x, y):
        particles = []
        colors    = [COLOR_RED, COLOR_ORANGE, COLOR_YELLOW, COLOR_WHITE]
        for _ in range(20):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.5, 5.0)
            vx    = math.cos(angle) * speed
            vy    = math.sin(angle) * speed
            color = random.choice(colors)
            life  = random.randint(15, self.LIFESPAN)
            radius= random.randint(2, 5)
            particles.append([x, y, vx, vy, color, life, radius])
        return particles

    def update(self):
        self.timer += 1
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.15   # 模拟重力
            p[5]  -= 1

        self.particles = [p for p in self.particles if p[5] > 0]
        if self.timer >= self.lifespan:
            self.kill()

    def draw(self, screen):
        #绘制
        for p in self.particles:
            alpha = max(0, int(255 * p[5] / self.lifespan))
            color = (*p[4][:3], alpha) if len(p[4]) == 3 else p[4]
            pygame.draw.circle(screen, p[4], (int(p[0]), int(p[1])), p[6])



#  游戏主控制器
class Game:
    TOTAL_ENEMIES = 12   # 本局敌机总数

    def __init__(self):
        pygame.init()
        pygame.font.init()
        self.screen  = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock   = pygame.time.Clock()

        self.resources   = ResourceManager("images")
        self.fontTitle   = pygame.font.SysFont("microsoftyahei", 48, bold=True)
        self.fontMenu    = pygame.font.SysFont("microsoftyahei", 24)
        self.fontSmall   = pygame.font.SysFont("microsoftyahei", 18)

        self._loadAllResources()
        self.state = GameState.START
        self._initGame()

    # 资源加载 
    def _loadAllResources(self):
        #统一加载游戏所需的所有图片资源。
        # 背景（7 张）
        self.backgrounds = self.resources.loadBackgrounds(7)

        # 三组敌机帧（每组 4 帧）
        self.enemyGroups = [
            self.resources.loadEnemyFrames(1),
            self.resources.loadEnemyFrames(2),
            self.resources.loadEnemyFrames(3),
        ]

        # 敌机子弹（4 张）
        self.enemyBulletImages = [
            self.resources.loadImage("enemyPlane_missile_01.png", (12, 24)),
            self.resources.loadImage("enemyPlane_missile_02.png", (12, 24)),
            self.resources.loadImage("enemyPlane_missile_03.png", (12, 24)),
            self.resources.loadImage("enemyPlane_missile_04.png", (12, 24)),
        ]

        # BOSS 和 BOSS 子弹
        self.bossImage       = self.resources.loadImage("enemyPlane_boss.png",        (120, 100))
        self.bossBulletImage = self.resources.loadImage("enemyPlane_missile_0100.png", (16, 16))

        # 玩家战机和子弹（3 张）
        self.playerImage       = self.resources.loadImage("myPlane.png",        (60, 70))
        self.playerBulletImages = [
            self.resources.loadImage("myPlane_missile_01_01.png", (10, 20)),
            self.resources.loadImage("myPlane_missile_01_02.png", (10, 20)),
            self.resources.loadImage("myPlane_missile_01_03.png", (10, 20)),
        ]

    # 游戏初始化 
    def _initGame(self):
        self.score      = 0
        self.boss       = None
        self.bossSpawned = False

        self.player        = PlayerPlane(self.playerImage, self.playerBulletImages)
        self.enemyGroup    = pygame.sprite.Group()
        self.explosionGroup = pygame.sprite.Group()

        self.spawner   = EnemySpawner(self.enemyGroups,
                                      self.enemyBulletImages,
                                      self.TOTAL_ENEMIES)
        self.bgScroller = BackgroundScroller(self.backgrounds)
        self.hud        = HUD()

    #  主循环 
    def run(self):
        while True:
            self.clock.tick(FPS)
            self._handleEvents()

            if self.state == GameState.START:
                self._updateStart()
                self._drawStart()
            elif self.state == GameState.PLAYING:
                self._updatePlaying()
                self._drawPlaying()
            elif self.state == GameState.WIN:
                self._drawEndScreen(win=True)
            elif self.state == GameState.LOSE:
                self._drawEndScreen(win=False)

            pygame.display.flip()

    # 事件处理 
    def _handleEvents(self):
        #处理退出和按键事件。
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                self._handleKeyDown(event.key)

    def _handleKeyDown(self, key):
        #响应键盘按下事件
        if self.state == GameState.START:
            if key == pygame.K_RETURN or key == pygame.K_SPACE:
                self.state = GameState.PLAYING
        elif self.state in (GameState.WIN, GameState.LOSE):
            if key == pygame.K_RETURN or key == pygame.K_r:
                self._initGame()
                self.state = GameState.PLAYING
            elif key == pygame.K_q or key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

    # 开始界面更新/绘制 
    def _updateStart(self):
        #开始界面
        self.bgScroller.update()

    def _drawStart(self):
        # 绘制开始界面
        self.bgScroller.draw(self.screen)

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))

        self._drawCenteredText("空  战  游  戏", self.fontTitle,
                               COLOR_YELLOW, SCREEN_HEIGHT // 2 - 80)
        self._drawCenteredText("按 Enter 或 空格 开始", self.fontMenu,
                               COLOR_WHITE, SCREEN_HEIGHT // 2 + 10)
        self._drawCenteredText("方向键移动  空格射击", self.fontSmall,
                               COLOR_GRAY, SCREEN_HEIGHT // 2 + 55)

    #  游戏进行中
    def _updatePlaying(self):
        #更新
        keys = pygame.key.get_pressed()

        self.bgScroller.update()
        self.player.update(keys)
        if keys[pygame.K_SPACE]:
            self.player.shoot()

        self._updateEnemies()
        self._updateBoss()
        self._checkCollisions()
        self._checkWinLose()
        self.explosionGroup.update()

    def _updateEnemies(self):
        #更新敌机。
        self.spawner.update(self.enemyGroup)
        for enemy in self.enemyGroup:
            enemy.update(self.player.rect)

    def _updateBoss(self):
        #生成 BOSS。
        if (not self.bossSpawned
                and self.spawner.finished
                and len(self.enemyGroup) == 0):
            self.boss        = Boss(self.bossImage, self.bossBulletImage)
            self.bossSpawned = True

        if self.boss:
            self.boss.update()

    def _checkCollisions(self):
        #检测所有碰撞并处理后果
        self._checkPlayerBulletsVsEnemies()
        self._checkPlayerBulletsVsBoss()
        self._checkEnemyBulletsVsPlayer()
        self._checkBossBulletsVsPlayer()
        self._checkEnemiesVsPlayer()

    def _checkPlayerBulletsVsEnemies(self):
        #玩家子弹击中敌机
        for bullet in list(self.player.bulletGroup):
            hitEnemies = pygame.sprite.spritecollide(
                bullet, self.enemyGroup, False,
                pygame.sprite.collide_rect)
            for enemy in hitEnemies:
                bullet.kill()
                if enemy.takeDamage(bullet.damage):
                    self.score += enemy.score
                    self._spawnExplosion(enemy.rect.centerx, enemy.rect.centery)
                    enemy.kill()

    def _checkPlayerBulletsVsBoss(self):
        #玩家子弹击中 BOSS
        if not self.boss:
            return
        for bullet in list(self.player.bulletGroup):
            if bullet.rect.colliderect(self.boss.rect):
                bullet.kill()
                if self.boss.takeDamage(bullet.damage):
                    self.score += self.boss.score
                    self._spawnExplosion(self.boss.rect.centerx,
                                        self.boss.rect.centery)
                    self.boss = None
                    break

    def _checkEnemyBulletsVsPlayer(self):
        #普通敌机子弹击中玩家。
        for enemy in self.enemyGroup:
            for bullet in list(enemy.bulletGroup):
                if bullet.rect.colliderect(self.player.rect):
                    bullet.kill()
                    if self.player.takeDamage(bullet.damage):
                        self.state = GameState.LOSE

    def _checkBossBulletsVsPlayer(self):
        #BOSS 子弹击中玩家
        if not self.boss:
            return
        for bullet in list(self.boss.bulletGroup):
            if bullet.rect.colliderect(self.player.rect):
                bullet.kill()
                if self.player.takeDamage(bullet.damage):
                    self.state = GameState.LOSE

    def _checkEnemiesVsPlayer(self):
        #敌机与玩家碰撞。
        for enemy in list(self.enemyGroup):
            if enemy.rect.colliderect(self.player.rect):
                self._spawnExplosion(enemy.rect.centerx, enemy.rect.centery)
                enemy.kill()
                if self.player.takeDamage(2):
                    self.state = GameState.LOSE

    def _checkWinLose(self):
        #检查胜利
        if self.bossSpawned and self.boss is None and self.state == GameState.PLAYING:
            self.state = GameState.WIN

    def _spawnExplosion(self, x, y):
       #生成爆炸效果。
        explosion = Explosion(x, y)
        self.explosionGroup.add(explosion)

    # 游戏进行中绘制 
    def _drawPlaying(self):
        #绘制游戏进行中的所有画面元素。
        self.bgScroller.draw(self.screen)

        for enemy in self.enemyGroup:
            enemy.draw(self.screen)

        if self.boss:
            self.boss.draw(self.screen)

        self.player.draw(self.screen)

        for explosion in self.explosionGroup:
            explosion.draw(self.screen)

        enemyLeft = len(self.enemyGroup) + (1 if self.boss else 0)
        self.hud.draw(self.screen, self.score, self.player.hp,
                      self.player.maxHp, enemyLeft)

    # 结束界面绘制 
    def _drawEndScreen(self, win):
        self.bgScroller.update()
        self.bgScroller.draw(self.screen)

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        if win:
            self._drawCenteredText("胜 利", self.fontTitle,
                                   COLOR_YELLOW, SCREEN_HEIGHT // 2 - 90)
            self._drawCenteredText("你消灭了所有敌机！", self.fontMenu,
                                   COLOR_GREEN, SCREEN_HEIGHT // 2 - 20)
        else:
            self._drawCenteredText(" 游戏结束 ", self.fontTitle,
                                   COLOR_RED, SCREEN_HEIGHT // 2 - 90)
            self._drawCenteredText("失败", self.fontMenu,
                                   COLOR_ORANGE, SCREEN_HEIGHT // 2 - 20)

        self._drawCenteredText(f"最终得分: {self.score}", self.fontMenu,
                               COLOR_CYAN, SCREEN_HEIGHT // 2 + 30)
        self._drawCenteredText("按 Enter / R 重新开始  |  Q 退出", self.fontSmall,
                               COLOR_GRAY, SCREEN_HEIGHT // 2 + 80)

    # 工具方法
    def _drawCenteredText(self, text, font,color, y):
        surface = font.render(text, True, color)
        x       = (SCREEN_WIDTH - surface.get_width()) // 2
        self.screen.blit(surface, (x, y))



if __name__ == "__main__":
    game = Game()
    game.run()
